"""
Measure a campaign: participation, costs, retention by group, and the wording of what the data supports.
"""

from datetime import date

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, norm
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analysis.stats import wilson_ci
from src.campaigns.constants import MAX_COVERAGE_GAP, MAX_SMD, MIN_OUTCOME_COVERAGE
from src.db.models import CampaignActivity, RetentionCampaign



NO_ATTRIBUTION = ("We can describe how many customers were retained, but we cannot say how many would have "
                  "stayed anyway, so no effect of the campaign can be claimed.")


def load_activities(db: Session, campaign_id: int) -> pd.DataFrame:
    t = CampaignActivity.__table__
    return pd.read_sql(select(t).where(t.c.campaign_id == campaign_id), db.connection())


# statistics
def minimum_detectable_effect(p: float, n_treat: int, n_control: int, alpha: float = 0.05,
                              power: float = 0.80) -> float:
    """
    Smallest difference in proportions (e.g. 0.06 = 6 points) the test would reliably detect (normal approximation).
    """
    z = norm.ppf(1 - alpha / 2) + norm.ppf(power)
    return float(z * np.sqrt(p * (1 - p) * (1 / n_treat + 1 / n_control)))


def newcombe_diff_ci(k1: int, n1: int, k2: int, n2: int):
    """
    95% CI for the difference of two proportions, built from Wilson intervals (Newcombe's method).
    """
    
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = (float(v) for v in wilson_ci(k1, n1))
    l2, u2 = (float(v) for v in wilson_ci(k2, n2))
    d = p1 - p2
    return (
        float(d - np.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)),
        float(d + np.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))
    )


# participation and cost
def participation(df: pd.DataFrame, today=None) -> dict:
    today = pd.Timestamp(today or date.today())
    t = df[df["assignment"] == "treatment"]
    attempted = int((t["contact_attempts"] > 0).sum())
    reached = int(t["outcome"].notna().sum())
    accepted = int((t["outcome"] == "accepted_offer").sum())
    due = pd.to_datetime(t["follow_up_date"])
    open_item = t["status"].isin(["pending", "attempted"]) | ((t["status"] == "contacted") & due.notna())
    
    return {
        "enrolled": int(len(df)), 
        "treatment": int(len(t)), 
        "control": int((df["assignment"] == "control").sum()),
        "attempted": attempted, "reached": reached,
        "reach_rate": reached / attempted if attempted else None,
        "unreachable": int((t["status"] == "unreachable").sum()),
        "still_pending": int((t["status"] == "pending").sum()),
        "overdue_follow_ups": int((open_item & (due < today)).sum()),
        "offers_accepted": accepted, 
        "acceptance_rate": accepted / reached if reached else None,
        "declined": int((t["outcome"] == "declined").sum()),
    }


def campaign_costs(df: pd.DataFrame, camp) -> dict:
    attempts = int(df["contact_attempts"].sum())
    accepted = int((df["outcome"] == "accepted_offer").sum())
    reached = int(df["outcome"].notna().sum())
    contact = attempts * camp.cost_per_contact
    incentives = accepted * camp.incentive_cost
    total = contact + incentives + camp.fixed_cost
    
    return {
        "contact_attempts": attempts, 
        "contact_cost": round(contact, 2),
        "offers_accepted": accepted, 
        "incentive_cost": round(incentives, 2),
        "fixed_cost": round(float(camp.fixed_cost), 2), 
        "total_cost": round(total, 2),
        "variable_cost_per_customer_reached": round((contact + incentives) / reached, 2) if reached else None
    }


# retention comparison
def retention_by_group(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    
    for g in ("treatment", "control"):
        d = df[df["assignment"] == g]
        if d.empty:
            continue
        known = d[d["retention_outcome"].notna()]
        n_known = len(known)
        retained = int((known["retention_outcome"] == "retained").sum())
        lo, hi = wilson_ci(retained, n_known) if n_known else (np.nan, np.nan)
        rows.append({
            "group": g, 
            "customers": len(d), 
            "outcomes_known": n_known,
            "coverage_pct": round(100 * n_known / len(d), 1), 
            "retained": retained,
            "retention_rate_pct": round(100 * retained / n_known, 1) if n_known else np.nan,
            "ci_low_pct": round(100 * float(lo), 1), 
            "ci_high_pct": round(100 * float(hi), 1)
        })

    return pd.DataFrame(rows)


def compare_groups(df: pd.DataFrame, camp) -> dict:
    """
    Assigned-to-campaign vs held-out (intention to treat). Valid as evidence about the campaign ONLY if randomised.
    """
    
    out = {"design": "randomised holdout" if camp.holdout_share > 0 else "no control group", "warnings": []}
    stats = {}
    for g in ("treatment", "control"):
        d = df[df["assignment"] == g]
        known = d[d["retention_outcome"].notna()]
        stats[g] = (len(d), len(known), int((known["retention_outcome"] == "retained").sum()))
    (n_t_all, n_t, k_t), (n_c_all, n_c, k_c) = stats["treatment"], stats["control"]
    if n_c_all == 0:
        return {**out, "computable": False, "reason": "the campaign has no control (holdout) group"}
    if n_t == 0 or n_c == 0:
        return {**out, "computable": False,
                "reason": "retention outcomes have not been recorded for both groups yet"}

    p_t, p_c = k_t / n_t, k_c / n_c
    lo, hi = newcombe_diff_ci(k_t, n_t, k_c, n_c)
    _, p_value = fisher_exact([[k_t, n_t - k_t], [k_c, n_c - k_c]])
    cov_t, cov_c = n_t / n_t_all, n_c / n_c_all
    if min(cov_t, cov_c) < MIN_OUTCOME_COVERAGE:
        out["warnings"].append(f"Outcome coverage is low (campaign {cov_t:.0%}, holdout {cov_c:.0%}); "
                               "results may be biased by who was followed up.")
    if abs(cov_t - cov_c) > MAX_COVERAGE_GAP:
        out["warnings"].append("Outcomes are known for very different shares of the two groups; "
                               "uneven follow-up can create a false difference.")
    return {
        **out, 
        "computable": True,
        "n_treatment": n_t, 
        "n_control": n_c, 
        "retained_treatment": k_t, 
        "retained_control": k_c,
        "rate_treatment_pct": round(100 * p_t, 1), 
        "rate_control_pct": round(100 * p_c, 1),
        "difference_pts": round(100 * (p_t - p_c), 2),
        "ci_low_pts": round(100 * lo, 2), 
        "ci_high_pts": round(100 * hi, 2),
        "p_value": float(p_value), 
        "coverage_treatment": cov_t, 
        "coverage_control": cov_c,
        "relative_churn_reduction_pct": round(100 * ((1 - p_c) - (1 - p_t)) / (1 - p_c), 1) if p_c < 1 else None
    }


def claim_text(res: dict) -> str:
    """
    The sentence the report is allowed to say. This is where over-claiming is prevented.
    """
    
    if not res.get("computable"):
        return f"No comparison is possible: {res.get('reason', 'not enough data')}. {NO_ATTRIBUTION}"
    
    d, lo, hi = res["difference_pts"], res["ci_low_pts"], res["ci_high_pts"]
    text = (f"Customers assigned to the campaign were retained at {res['rate_treatment_pct']:.1f}% versus "
            f"{res['rate_control_pct']:.1f}% in the randomised holdout group (difference {d:+.1f} points, "
            f"95% CI {lo:+.1f} to {hi:+.1f}; n = {res['n_treatment']} vs {res['n_control']}). ")
    if lo > 0:
        text += ("Because customers were assigned at random, this gap is unlikely to be chance and can be "
                 "attributed to the campaign (measured per customer assigned, whether or not each was reached).")
    elif hi < 0:
        text += "The campaign group was retained LESS often than the holdout group: review the campaign for harm."
    else:
        text += ("The interval includes zero, so these data do not show that the campaign changed retention. "
                 "The true effect may be zero, small or positive; a larger holdout would be needed to tell.")
    if res.get("warnings"):
        text += " Treat this with caution: see the data-quality warnings."
    return text


def economics(res: dict, n_treatment: int, avg_annual_value: float, total_cost: float):
    """
    Money impact, only when the randomised comparison is available. Uses the CI so uncertainty is visible.
    """
    
    if not res.get("computable"):
        return None
    people = lambda pts: pts / 100 * n_treatment            # difference in points -> extra customers retained
    extra, extra_lo, extra_hi = (people(res[k]) for k in ("difference_pts", "ci_low_pts", "ci_high_pts"))
    return {
        "additional_retained": extra, 
        "additional_retained_low": extra_lo, 
        "additional_retained_high": extra_hi,
        "incremental_revenue": extra * avg_annual_value, 
        "total_cost": total_cost,
        "net_benefit": extra * avg_annual_value - total_cost,
        "net_low": extra_lo * avg_annual_value - total_cost,
        "net_high": extra_hi * avg_annual_value - total_cost,
        "roi": (extra * avg_annual_value - total_cost) / total_cost if total_cost > 0 else None,
        "cost_per_additional_retained": total_cost / extra if extra > 0 else None
    }


# diagnostics
def balance_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Did randomisation produce similar groups at enrolment? SMD = difference in means / pooled spread.
    """
    
    t, c = df[df["assignment"] == "treatment"], df[df["assignment"] == "control"]
    if len(t) < 2 or len(c) < 2:
        return pd.DataFrame()
    d = df.assign(month_to_month=(df["contract_type_at_enrollment"] == "Month-to-month").astype(int))
    t, c = d[d["assignment"] == "treatment"], d[d["assignment"] == "control"]
    cols = {
        "probability_at_enrollment": "Churn probability at enrolment",
        "monthly_charges_at_enrollment": "Monthly charges",
        "tenure_at_enrollment": "Tenure (months)", 
        "month_to_month": "Share on month-to-month"
    }

    rows = []
    for col, label in cols.items():
        pooled = np.sqrt((t[col].var(ddof=1) + c[col].var(ddof=1)) / 2)
        smd = (t[col].mean() - c[col].mean()) / pooled if pooled > 0 else 0.0
        rows.append({"measure": label, "campaign_group": round(float(t[col].mean()), 3),
                     "holdout_group": round(float(c[col].mean()), 3), "smd": round(float(smd), 3)})
    return pd.DataFrame(rows)


def reached_vs_not(df: pd.DataFrame) -> pd.DataFrame:
    """
    DESCRIPTIVE ONLY. Reached customers differ from unreached ones before any contact, so this is not like-for-like.
    """
    
    t = df[(df["assignment"] == "treatment") & df["retention_outcome"].notna()].copy()
    if t.empty:
        return pd.DataFrame()
    t["contact"] = np.where(t["outcome"].notna(), "reached", "not reached")
    t["retained_flag"] = (t["retention_outcome"] == "retained").astype(int)
    g = t.groupby("contact").agg(customers=("activity_id", "size"),
                                 avg_risk_at_enrolment=("probability_at_enrollment", "mean"),
                                 retention_rate=("retained_flag", "mean")).reset_index()
    g["avg_risk_at_enrolment_pct"] = (100 * g.pop("avg_risk_at_enrolment")).round(1)
    g["retention_rate_pct"] = (100 * g.pop("retention_rate")).round(1)
    return g


def lift_by(df: pd.DataFrame, col: str, min_n: int = 30) -> pd.DataFrame:
    """
    Exploratory: assigned-vs-holdout retention inside each subgroup. Subgroups are small, so treat with care.
    """
    
    known = df[df["retention_outcome"].notna()].copy()
    known["retained_flag"] = (known["retention_outcome"] == "retained").astype(int)
    rows = []
    for value, g in known.groupby(col):
        t, c = g[g["assignment"] == "treatment"], g[g["assignment"] == "control"]
        rows.append({
            col: value, 
            "campaign_n": len(t), 
            "holdout_n": len(c),
            "campaign_retention_pct": round(100 * t["retained_flag"].mean(), 1) if len(t) else np.nan,
            "holdout_retention_pct": round(100 * c["retained_flag"].mean(), 1) if len(c) else np.nan,
            "difference_pts": (round(100 * (t["retained_flag"].mean() - c["retained_flag"].mean()), 1)
                                        if len(t) and len(c) else np.nan),
            "reliable": len(t) >= min_n and len(c) >= min_n
        })

    return pd.DataFrame(rows)


def analyse(db: Session, campaign_id: int, today=None) -> dict:
    camp = db.get(RetentionCampaign, campaign_id)
    if camp is None:
        raise ValueError(f"Campaign {campaign_id} does not exist.")
    df = load_activities(db, campaign_id)
    costs = campaign_costs(df, camp)
    comparison = compare_groups(df, camp)
    bal = balance_table(df)
    if not bal.empty and (bal["smd"].abs() > MAX_SMD).any():
        off = ", ".join(bal.loc[bal["smd"].abs() > MAX_SMD, "measure"])
        comparison["warnings"].append(f"The two groups differ noticeably at enrolment on: {off}.")
    comparison["claim"] = claim_text(comparison)
    t = df[df["assignment"] == "treatment"]
    avg_value = float(t["monthly_charges_at_enrollment"].mean() * camp.value_horizon_months) if len(t) else 0.0
    
    return {
        "campaign": camp, 
        "df": df, 
        "participation": participation(df, today), 
        "costs": costs,
        "retention": retention_by_group(df), 
        "comparison": comparison,
        "economics": economics(comparison, len(t), avg_value, costs["total_cost"]),
        "balance": bal, 
        "reached_vs_not": reached_vs_not(df),
        "by_segment": lift_by(df, "priority_segment_at_enrollment")
    }

