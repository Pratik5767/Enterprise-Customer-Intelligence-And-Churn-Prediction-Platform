"""
Choose which customers a campaign targets, randomise a holdout group, and spread work across reps.
"""

import numpy as np
import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.campaigns.analysis import minimum_detectable_effect
from src.campaigns.constants import DEFAULT_HOLDOUT_SHARE, MIN_CONTROL_SIZE, STALE_SCORES_DAYS
from src.db.models import CampaignActivity, RetentionCampaign
from src.ml.settings import HORIZON_MONTHS



# The latest stored prediction for every customer who is still active (Module 4 wrote these)
ELIGIBLE_SQL = """
    SELECT 
        p.prediction_id, 
        p.customer_id, 
        p.probability, 
        p.risk_level, 
        p.value_tier,
        p.priority_segment, 
        p.priority_rank, 
        p.flagged_for_review, 
        p.prediction_date,
        c.monthly_charges, 
        c.tenure, 
        c.contract_type
    FROM churn_predictions p
    JOIN (
        SELECT 
            customer_id, 
            MAX(prediction_id) AS last_id
        FROM churn_predictions 
        WHERE customer_id IS NOT NULL 
        GROUP BY customer_id
    ) m
    ON p.prediction_id = m.last_id
    JOIN customers c ON c.customer_id = p.customer_id
    WHERE c.subscription_status = 'active'
"""

RULE_KEYS = {
    "priority_ranks", 
    "priority_segments", 
    "risk_levels", 
    "value_tiers",
    "contract_types", 
    "min_probability", 
    "flagged_only", 
    "max_customers"
}


def load_eligible(db: Session) -> pd.DataFrame:
    df = pd.read_sql(text(ELIGIBLE_SQL), db.connection())
    df["expected_revenue_at_risk"] = (df["probability"] * df["monthly_charges"] * HORIZON_MONTHS).round(2)
    return df


def customers_in_open_campaigns(db: Session) -> set:
    """
    Customers enrolled (treatment OR control) in a draft/active campaign. They must not be reused.
    """
    
    stmt = (
        select(CampaignActivity.customer_id).select_from(CampaignActivity)
            .join(RetentionCampaign, RetentionCampaign.campaign_id == CampaignActivity.campaign_id)
            .where(RetentionCampaign.status.in_(["draft", "active"]))
        )
    return set(db.scalars(stmt))


def apply_rule(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    """
    Filter eligible customers with a rule such as {"priority_ranks": [1, 2], "max_customers": 500}.
    """
    
    unknown = set(rule) - RULE_KEYS
    if unknown:                                   # a typo must not silently select the wrong people
        raise ValueError(f"Unknown selection-rule keys {sorted(unknown)}. Allowed: {sorted(RULE_KEYS)}")
    out = df
    
    for key, column in [
        ("priority_ranks", "priority_rank"), 
        ("priority_segments", "priority_segment"),
        ("risk_levels", "risk_level"), ("value_tiers", "value_tier"),
        ("contract_types", "contract_type")
    ]:
        if key in rule:
            out = out[out[column].isin(rule[key])]
    
    if "min_probability" in rule:
        out = out[out["probability"] >= rule["min_probability"]]
    if rule.get("flagged_only"):
        out = out[out["flagged_for_review"].astype(bool)]
    out = out.sort_values("expected_revenue_at_risk", ascending=False)
    if "max_customers" in rule:
        out = out.head(int(rule["max_customers"]))
    
    return out.reset_index(drop=True)


def _candidates(db: Session):
    eligible = load_eligible(db)
    if eligible.empty:
        raise RuntimeError("No scored customers found. Run: python -m src.ml.segment_run")
    locked = customers_in_open_campaigns(db)
    free = eligible[~eligible["customer_id"].isin(locked)]
    newest = pd.to_datetime(eligible["prediction_date"], utc=True).max()
    age_days = (pd.Timestamp.now(tz="UTC") - newest).days
    return free, len(eligible) - len(free), int(age_days)


def select_customers(db: Session, rule: dict) -> pd.DataFrame:
    free, _, _ = _candidates(db)
    return apply_rule(free, rule)


def preview(db: Session, rule: dict, holdout_share: float = DEFAULT_HOLDOUT_SHARE) -> dict:
    """
    What would this rule select, and what could the resulting test detect? Nothing is saved.
    """
    
    free, n_locked, age_days = _candidates(db)
    sel = apply_rule(free, rule)
    n = len(sel)
    n_control = int(round(n * holdout_share))
    n_treat = n - n_control
    
    out = {"matching_customers": n, "treatment": n_treat, "control": n_control,
           "excluded_already_in_open_campaign": n_locked, "scores_age_days": age_days,
           "avg_churn_probability": round(float(sel["probability"].mean()), 3) if n else None,
           "expected_revenue_at_risk": round(float(sel["expected_revenue_at_risk"].sum())) if n else 0,
           "detectable_difference_pts": None, "warnings": []}
    
    if n_treat and n_control:
        mde = minimum_detectable_effect(float(sel["probability"].mean()), n_treat, n_control)
        out["detectable_difference_pts"] = round(100 * mde, 1)
    if n == 0:
        out["warnings"].append("The rule matches no eligible customers.")
    if age_days > STALE_SCORES_DAYS:
        out["warnings"].append(f"Risk scores are {age_days} days old. Re-run: python -m src.ml.segment_run")
    if holdout_share == 0:
        out["warnings"].append("No holdout: results will be descriptive only (no claim about cause is possible).")
    elif 0 < n_control < MIN_CONTROL_SIZE:
        out["warnings"].append(f"Control group would have only {n_control} customers; only large effects "
                               f"(about {out['detectable_difference_pts']} points or more) would be detectable.")
    return out


def assign_groups(selected: pd.DataFrame, holdout_share: float, seed: int, strata_col: str = "priority_segment") -> pd.Series:
    """
    Randomly hold out `holdout_share` of customers, separately inside each segment (stratified).
    """
    
    if not 0 <= holdout_share < 1:
        raise ValueError("holdout_share must be at least 0 and below 1")
    groups = pd.Series("treatment", index=selected.index, dtype=object)
    if holdout_share == 0:
        return groups
    rng = np.random.default_rng(seed)
    for _, idx in selected.groupby(strata_col, sort=True).groups.items():
        idx = np.array(list(idx))
        n_control = int(round(len(idx) * holdout_share))
        if n_control:
            groups.loc[rng.permutation(idx)[:n_control]] = "control"
    return groups


def assign_reps(treatment: pd.DataFrame, reps: list, max_per_rep: int | None = None) -> pd.Series:
    """
    Round-robin over customers sorted by priority, so every rep gets a similar mix of urgent and routine work.
    """
    
    if not reps:
        raise ValueError("Assign at least one customer-success rep.")
    
    if max_per_rep is not None and len(treatment) > max_per_rep * len(reps):
        raise ValueError(f"{len(treatment)} customers exceed team capacity ({len(reps)} reps x {max_per_rep}).")
    
    order = (
            treatment.assign(_value=treatment["probability"] * treatment["monthly_charges"])
                    .sort_values(["priority_rank", "_value"], ascending=[True, False])
        )
    
    return pd.Series([reps[i % len(reps)] for i in range(len(order))], index=order.index)

