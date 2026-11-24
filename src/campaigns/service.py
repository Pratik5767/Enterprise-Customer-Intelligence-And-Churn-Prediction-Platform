"""
Campaign workflow: create, launch, log outreach, record outcomes.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.campaigns.constants import (CAMPAIGN_TRANSITIONS, CAMPAIGN_TYPES, DEFAULT_HOLDOUT_SHARE,
                                     DEFAULT_OUTCOME_WINDOW_DAYS, FOLLOW_UP_AFTER_CONTACT_DAYS,
                                     FOLLOW_UP_DAYS_BY_RANK, FOLLOW_UP_OUTCOMES, MAX_ATTEMPTS,
                                     MIN_CONTROL_SIZE, OUTCOMES, OUTREACH_STATUSES, RETRY_DAYS)
from src.campaigns.selection import assign_groups, assign_reps, customers_in_open_campaigns
from src.db.models import CampaignActivity, RetentionCampaign
from src.ml.settings import CONTACT_COST, HORIZON_MONTHS



REQUIRED_COLUMNS = {"prediction_id", "customer_id", "probability", "risk_level", "priority_segment",
                    "priority_rank", "monthly_charges", "tenure", "contract_type"}


class CampaignError(ValueError):
    """A request that breaks a campaign rule. The API will turn this into a 400/409 response."""


@dataclass
class CampaignSpec:
    name: str
    campaign_type: str
    owner: str
    reps: list
    start_date: date
    target_segment: str                       # readable description, e.g. "Critical + Priority customers"
    selection_rule: dict
    holdout_share: float = DEFAULT_HOLDOUT_SHARE
    cost_per_contact: float = CONTACT_COST    # per outreach attempt (same placeholder as Module 3)
    incentive_cost: float = 0.0               # per accepted offer
    fixed_cost: float = 0.0
    outcome_window_days: int = DEFAULT_OUTCOME_WINDOW_DAYS
    value_horizon_months: int = HORIZON_MONTHS
    max_per_rep: Optional[int] = None
    seed: int = 42
    is_synthetic: bool = False


# helpers
def _get_campaign(db: Session, campaign_id: int) -> RetentionCampaign:
    camp = db.get(RetentionCampaign, campaign_id)
    if camp is None:
        raise CampaignError(f"Campaign {campaign_id} does not exist.")
    return camp


def _get_activity(db: Session, activity_id: int):
    act = db.get(CampaignActivity, activity_id)
    if act is None:
        raise CampaignError(f"Activity {activity_id} does not exist.")
    return act, db.get(RetentionCampaign, act.campaign_id)


def _save(db: Session, commit: bool) -> None:
    db.commit() if commit else db.flush()


def _check_spec(db: Session, spec: CampaignSpec) -> None:
    if spec.campaign_type not in CAMPAIGN_TYPES:
        raise CampaignError(f"campaign_type must be one of {CAMPAIGN_TYPES}")
    if not spec.name.strip():
        raise CampaignError("The campaign needs a name.")
    if db.scalar(select(RetentionCampaign.campaign_id).where(RetentionCampaign.campaign_name == spec.name.strip())):
        raise CampaignError(f"A campaign named '{spec.name}' already exists.")
    if not spec.owner.strip():
        raise CampaignError("The campaign needs an owner.")
    if not spec.reps or len(set(spec.reps)) != len(spec.reps):
        raise CampaignError("Give a non-empty list of distinct reps.")
    if not 0 <= spec.holdout_share < 1:
        raise CampaignError("holdout_share must be at least 0 and below 1.")
    if min(spec.cost_per_contact, spec.incentive_cost, spec.fixed_cost) < 0:
        raise CampaignError("Costs cannot be negative.")
    if spec.outcome_window_days < 1:
        raise CampaignError("outcome_window_days must be at least 1.")


def _check_selected(db: Session, selected: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(selected.columns)
    if missing:
        raise CampaignError(f"The selection is missing columns: {sorted(missing)}")
    if selected.empty:
        raise CampaignError("The selection is empty: no eligible customers to enrol.")
    if selected["customer_id"].duplicated().any():
        raise CampaignError("The selection contains the same customer more than once.")
    clash = set(selected["customer_id"]) & customers_in_open_campaigns(db)
    if clash:
        raise CampaignError(f"{len(clash)} selected customers are already in another open campaign "
                            f"(for example {sorted(clash)[:3]}). A customer can be in only one at a time.")


def _activity_row(campaign_id: int, r, rep_of: pd.Series, base_date: date) -> CampaignActivity:
    treated = r.assignment == "treatment"
    due = base_date + timedelta(days=FOLLOW_UP_DAYS_BY_RANK.get(int(r.priority_rank), 14))
    return CampaignActivity(
        campaign_id=campaign_id, customer_id=str(r.customer_id), assignment=r.assignment,
        assigned_to=rep_of.get(r.Index) if treated else None,
        status="pending" if treated else "held_out",
        follow_up_date=due if treated else None, contact_attempts=0,
        prediction_id=int(r.prediction_id), probability_at_enrollment=float(r.probability),
        risk_level_at_enrollment=str(r.risk_level), priority_segment_at_enrollment=str(r.priority_segment),
        priority_rank_at_enrollment=int(r.priority_rank),
        monthly_charges_at_enrollment=float(r.monthly_charges),
        tenure_at_enrollment=int(r.tenure), contract_type_at_enrollment=str(r.contract_type))


def _enroll(db, camp, selected, reps, base_date, max_per_rep, seed):
    sel = selected.reset_index(drop=True)
    sel["assignment"] = assign_groups(sel, camp.holdout_share, seed)
    if camp.holdout_share > 0 and not (sel["assignment"] == "control").any():
        raise CampaignError("The holdout share is too small to create a control group from this many customers.")
    treat = sel[sel["assignment"] == "treatment"]
    try:
        rep_of = assign_reps(treat, reps, max_per_rep)
    except ValueError as e:
        raise CampaignError(str(e)) from e
    db.add_all([_activity_row(camp.campaign_id, r, rep_of, base_date) for r in sel.itertuples()])
    return sel, rep_of


# campaign lifecycle
def create_campaign(db: Session, spec: CampaignSpec, selected: pd.DataFrame) -> dict:
    """
    Create a DRAFT campaign, randomise the holdout, assign reps and follow-up dates.
    """
    
    _check_spec(db, spec)
    _check_selected(db, selected)
    camp = RetentionCampaign(
        campaign_name=spec.name.strip(), campaign_type=spec.campaign_type, target_segment=spec.target_segment,
        selection_rule=spec.selection_rule, owner=spec.owner, status="draft", start_date=spec.start_date,
        outcome_window_days=spec.outcome_window_days, holdout_share=spec.holdout_share,
        randomization_seed=spec.seed, cost_per_contact=spec.cost_per_contact,
        incentive_cost=spec.incentive_cost, fixed_cost=spec.fixed_cost,
        value_horizon_months=spec.value_horizon_months, is_synthetic=spec.is_synthetic
    )

    try:
        db.add(camp)
        db.flush()                                   # assigns camp.campaign_id
        cid = camp.campaign_id
        sel, rep_of = _enroll(db, camp, selected, spec.reps, spec.start_date, spec.max_per_rep, spec.seed)
        db.commit()
    except Exception:
        db.rollback()
        raise

    n_control = int((sel["assignment"] == "control").sum())
    warnings = []
    if spec.holdout_share == 0:
        warnings.append("No holdout group: results can only be descriptive (no claim about cause).")
    elif n_control < MIN_CONTROL_SIZE:
        warnings.append(f"Control group has only {n_control} customers; only large effects will be detectable.")
    return {"campaign_id": cid, "enrolled": len(sel), "treatment": len(sel) - n_control,
            "control": n_control, "per_rep": rep_of.value_counts().to_dict(), "warnings": warnings}


def add_customers(db: Session, campaign_id: int, selected: pd.DataFrame, reps: list,
                  max_per_rep: Optional[int] = None, seed: Optional[int] = None) -> dict:
    """
    Enrol more customers into a draft/active campaign (this batch is randomised on its own).
    """
    
    camp = _get_campaign(db, campaign_id)
    if camp.status not in ("draft", "active"):
        raise CampaignError(f"Customers cannot be added to a {camp.status} campaign.")
    _check_selected(db, selected)
    if seed is None:
        seed = (camp.randomization_seed or 0) + 1
    try:
        sel, _ = _enroll(db, camp, selected, reps, max(camp.start_date, date.today()), max_per_rep, seed)
        db.commit()
    except Exception:
        db.rollback()
        raise
    n_control = int((sel["assignment"] == "control").sum())
    return {"added": len(sel), "treatment": len(sel) - n_control, "control": n_control}


def _move(camp: RetentionCampaign, new_status: str) -> None:
    if new_status not in CAMPAIGN_TRANSITIONS[camp.status]:
        raise CampaignError(f"A {camp.status} campaign cannot become {new_status}.")
    camp.status = new_status


def launch_campaign(db: Session, campaign_id: int) -> dict:
    camp = _get_campaign(db, campaign_id)
    n_treat = db.scalar(select(func.count()).select_from(CampaignActivity).where(
        CampaignActivity.campaign_id == campaign_id, CampaignActivity.assignment == "treatment"))
    if not n_treat:
        raise CampaignError("Cannot launch a campaign with no customers to contact.")
    _move(camp, "active")
    db.commit()
    return {"campaign_id": campaign_id, "status": "active"}


def cancel_campaign(db: Session, campaign_id: int) -> dict:
    camp = _get_campaign(db, campaign_id)
    _move(camp, "cancelled")
    db.commit()
    return {"campaign_id": campaign_id, "status": "cancelled"}


def complete_campaign(db: Session, campaign_id: int, end_date: Optional[date] = None) -> dict:
    camp = _get_campaign(db, campaign_id)
    _move(camp, "completed")
    camp.end_date = end_date or date.today()
    missing = db.scalar(select(func.count()).select_from(CampaignActivity).where(
        CampaignActivity.campaign_id == campaign_id, CampaignActivity.retention_outcome.is_(None)))
    db.commit()
    warnings = []
    due = camp.start_date + timedelta(days=camp.outcome_window_days)
    if date.today() < due:
        warnings.append(f"Retention outcomes are not due until {due}; compare both groups at the same date.")
    if missing:
        warnings.append(f"{missing} customers still have no retention outcome recorded.")
    return {"campaign_id": campaign_id, "status": "completed", "end_date": camp.end_date,
            "outcomes_missing": int(missing), "warnings": warnings}


# day-to-day work
def log_outreach(db: Session, activity_id: int, *, reached: bool, outcome: Optional[str] = None,
                 notes: Optional[str] = None, on: Optional[date] = None, commit: bool = True) -> dict:
    """
    Record ONE contact attempt. reached=True needs an outcome; reached=False moves the customer toward 'unreachable'.
    """
    
    on = on or date.today()
    act, camp = _get_activity(db, activity_id)
    if camp.status != "active":
        raise CampaignError(f"Campaign '{camp.campaign_name}' is {camp.status}; "
                            "outreach can only be logged while it is active.")
    if act.assignment == "control":
        raise CampaignError("This customer is in the control (holdout) group and must not be contacted "
                            "by this campaign.")
    if act.status not in OUTREACH_STATUSES:
        raise CampaignError(f"Outreach cannot be logged for an activity that is {act.status}.")
    if reached and outcome not in OUTCOMES:
        raise CampaignError(f"A reached customer needs an outcome: {OUTCOMES}")
    if not reached and outcome is not None:
        raise CampaignError("An unreached customer cannot have an outcome.")

    act.contact_attempts += 1
    act.last_contact_at = datetime.now(timezone.utc)
    if notes:
        act.notes = notes[:500]
    if reached:
        act.status, act.outcome = "contacted", outcome
        act.follow_up_date = (on + timedelta(days=FOLLOW_UP_AFTER_CONTACT_DAYS)
                              if outcome in FOLLOW_UP_OUTCOMES else None)
    elif act.status == "contacted":                      # a follow-up call went unanswered: stay 'contacted'
        act.follow_up_date = on + timedelta(days=RETRY_DAYS)
    elif act.contact_attempts >= MAX_ATTEMPTS:
        act.status, act.follow_up_date = "unreachable", None
    else:
        act.status, act.follow_up_date = "attempted", on + timedelta(days=RETRY_DAYS)
    _save(db, commit)
    return {"activity_id": activity_id, "status": act.status,
            "contact_attempts": act.contact_attempts, "follow_up_date": act.follow_up_date}


def record_retention_outcome(db: Session, activity_id: int, *, retained: bool,
                             outcome_date: Optional[date] = None, overwrite: bool = False,
                             commit: bool = True) -> dict:
    """
    Record whether the customer stayed. Works for BOTH groups; record it at the end of the window for everyone.
    """
    act, camp = _get_activity(db, activity_id)
    if camp.status not in ("active", "completed"):
        raise CampaignError(f"Campaign '{camp.campaign_name}' is {camp.status}; outcomes cannot be recorded yet.")
    
    if act.retention_outcome and not overwrite:
        raise CampaignError("A retention outcome is already recorded; pass overwrite=True to change it.")
    
    act.retention_outcome = "retained" if retained else "churned"
    act.retention_outcome_date = outcome_date or date.today()
    
    _save(db, commit)
    
    return {"activity_id": activity_id, "retention_outcome": act.retention_outcome}


_CHURNED, _STAYED = {"yes", "churned", "1", "true"}, {"no", "retained", "0", "false"}


def _is_churned(value) -> bool:
    v = str(value).strip().lower()
    if v in _CHURNED:
        return True
    if v in _STAYED:
        return False
    raise CampaignError(f"Unrecognised churn value: {value!r}")


def record_outcomes_from_snapshot(db: Session, campaign_id: int, snapshot: pd.DataFrame,
                                  outcome_date: Optional[date] = None, overwrite: bool = False) -> dict:
    """
    Bulk-record outcomes from a status export with columns customer_id and churn (Yes/No).
    """
    
    _get_campaign(db, campaign_id)
    if not {"customer_id", "churn"} <= set(snapshot.columns):
        raise CampaignError("The snapshot needs the columns: customer_id, churn")
    status_of = dict(zip(snapshot["customer_id"].astype(str), snapshot["churn"]))
    acts = db.scalars(select(CampaignActivity).where(CampaignActivity.campaign_id == campaign_id)).all()
    updated = skipped = not_in_snapshot = 0
    for a in acts:
        if a.customer_id not in status_of:
            not_in_snapshot += 1
        elif a.retention_outcome and not overwrite:
            skipped += 1
        else:
            a.retention_outcome = "churned" if _is_churned(status_of[a.customer_id]) else "retained"
            a.retention_outcome_date = outcome_date or date.today()
            updated += 1
    db.commit()
    return {"updated": updated, "already_recorded": skipped, "not_in_snapshot": not_in_snapshot}


def reassign_activity(db: Session, activity_id: int, new_rep: str) -> dict:
    act, camp = _get_activity(db, activity_id)
    if act.assignment == "control":
        raise CampaignError("Control (holdout) customers have no rep.")
    if camp.status not in ("draft", "active"):
        raise CampaignError(f"Cannot reassign work in a {camp.status} campaign.")
    act.assigned_to = new_rep
    db.commit()
    return {"activity_id": activity_id, "assigned_to": new_rep}


def reschedule_follow_up(db: Session, activity_id: int, new_date: date) -> dict:
    act, _ = _get_activity(db, activity_id)
    if act.assignment == "control" or act.status not in OUTREACH_STATUSES:
        raise CampaignError("Only open treatment activities can be rescheduled.")
    act.follow_up_date = new_date
    db.commit()
    return {"activity_id": activity_id, "follow_up_date": new_date}


def follow_up_queue(db: Session, rep: str, as_of: Optional[date] = None) -> pd.DataFrame:
    """
    A rep's open work, overdue items first, then by date and priority.
    """
    
    as_of = as_of or date.today()
    a, c = CampaignActivity, RetentionCampaign
    open_work = a.status.in_(["pending", "attempted"]) | ((a.status == "contacted") & a.follow_up_date.is_not(None))
    stmt = (select(a.activity_id, c.campaign_name, a.customer_id, a.assigned_to, a.status, a.follow_up_date,
                   a.contact_attempts, a.priority_rank_at_enrollment.label("priority_rank"),
                   a.priority_segment_at_enrollment.label("priority_segment"), a.probability_at_enrollment)
            .select_from(a).join(c, c.campaign_id == a.campaign_id)
            .where(a.assigned_to == rep, c.status == "active", open_work))
    df = pd.read_sql(stmt, db.connection())
    if df.empty:
        df["overdue"] = pd.Series(dtype=bool)
        return df
    df["overdue"] = pd.to_datetime(df["follow_up_date"]) < pd.Timestamp(as_of)
    return (df.sort_values(["overdue", "follow_up_date", "priority_rank"], ascending=[False, True, True])
              .reset_index(drop=True))


def delete_synthetic_campaigns(db: Session) -> int:
    """
    Remove demo campaigns (is_synthetic = True) and their activities. Real campaigns are never touched.
    """
    
    ids = db.scalars(select(RetentionCampaign.campaign_id).where(RetentionCampaign.is_synthetic.is_(True))).all()
    if ids:
        db.execute(delete(CampaignActivity).where(CampaignActivity.campaign_id.in_(ids)))
        db.execute(delete(RetentionCampaign).where(RetentionCampaign.campaign_id.in_(ids)))
    db.commit()
    return len(ids)

