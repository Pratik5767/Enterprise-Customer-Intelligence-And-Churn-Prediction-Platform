"""
Customer-level prediction report: profile, latest risk assessment, history, campaign involvement.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analysis.run_eda import md_table
from src.db.models import CampaignActivity, ChurnPrediction, Customer, RetentionCampaign
from src.ml.explain import factors_text
from src.ml.segmentation import PREDICTION_NOTICE, RANK_ACTIONS, plain_language
from src.reporting.settings import SYNTHETIC_PREFIX



def customer_report(db: Session, customer_id: str):
    """
    Everything known about one customer, or None if the customer does not exist.
    """
    
    cust = db.get(Customer, customer_id)
    
    if cust is None:
        return None
    
    preds = db.scalars(select(ChurnPrediction).where(ChurnPrediction.customer_id == customer_id)
                       .order_by(ChurnPrediction.prediction_date, ChurnPrediction.prediction_id)).all()
    
    latest = None
    if preds:
        p = preds[-1]
        latest = {
            "probability": float(p.probability), 
            "risk_level": p.risk_level, 
            "value_tier": p.value_tier,
            "priority_segment": p.priority_segment, 
            "priority_rank": int(p.priority_rank),
            "flagged_for_review": bool(p.flagged_for_review), 
            "threshold": float(p.threshold),
            "model_version": p.model_version, 
            "source": p.source, 
            "scored_on": str(p.prediction_date)[:16],
            "risk_factors": p.top_risk_factors or [], 
            "protective_factors": p.top_protective_factors or []
        }

    hist = pd.DataFrame([{
        "scored_on": str(p.prediction_date)[:16],
        "batch": p.batch_id + (" (synthetic)" if p.batch_id.startswith(SYNTHETIC_PREFIX) else ""),
        "model_version": p.model_version, 
        "probability": round(float(p.probability), 3),
        "risk_level": p.risk_level, 
        "flagged": bool(p.flagged_for_review)
    } for p in preds])

    rows = db.execute(
        select(
            RetentionCampaign.campaign_name, 
            RetentionCampaign.status.label("campaign_status"),
            RetentionCampaign.is_synthetic, 
            CampaignActivity.assignment,
            CampaignActivity.status.label("activity_status"), 
            CampaignActivity.assigned_to,
            CampaignActivity.follow_up_date, 
            CampaignActivity.outcome, 
            CampaignActivity.retention_outcome
        )
        .select_from(CampaignActivity)
        .join(RetentionCampaign, RetentionCampaign.campaign_id == CampaignActivity.campaign_id)
        .where(CampaignActivity.customer_id == customer_id).order_by(CampaignActivity.activity_id)
    ).all()

    campaigns = [dict(r._mapping) for r in rows]
    # Holdout customers of an open campaign must not be contacted by it 
    do_not_contact = [
        c["campaign_name"] for c in campaigns
        if c["assignment"] == "control" and c["campaign_status"] in ("draft", "active")
    ]

    return {
        "customer_id": customer_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "profile": {
            "status": cust.subscription_status, 
            "tenure_months": cust.tenure,
            "contract_type": cust.contract_type, 
            "internet_service": cust.internet_service,
            "payment_method": cust.payment_method, 
            "monthly_charges": cust.monthly_charges,
            "total_charges": cust.total_charges, 
            "subscription_start": str(cust.subscription_start)
        },
        "latest": latest, 
        "history": hist, 
        "campaigns": campaigns, 
        "do_not_contact": do_not_contact
    }


def render_markdown(rep: dict) -> str:
    prof = rep["profile"]
    
    L = [f"# Customer report: {rep['customer_id']}", "", f"*Generated {rep['generated_at']}*", "",
         f"> {PREDICTION_NOTICE}", ""]
    
    if rep["do_not_contact"]:
        L += [f"**DO NOT CONTACT for: {', '.join(rep['do_not_contact'])}.** This customer is in the holdout (control) "
              "group of an open campaign, and contacting them would invalidate the campaign's measurement.", ""]
    
    L += ["## Profile", "",
          md_table(pd.DataFrame({"item": list(prof), "value": [str(v) for v in prof.values()]})), ""]

    lt = rep["latest"]
    L += ["## Current risk assessment", ""]
    
    if lt is None:
        L += ["No prediction is stored for this customer.", ""]
    else:
        L += [md_table(pd.DataFrame([
            ("Churn probability", f"{lt['probability']:.1%}"), ("Risk level", lt["risk_level"]),
            ("Value tier", lt["value_tier"]), ("Priority segment", lt["priority_segment"]),
            ("Flagged for review", "yes" if lt["flagged_for_review"] else "no"),
            ("Review threshold", f"{lt['threshold']:.2f}"),
            ("Model / source / scored on", f"{lt['model_version']} / {lt['source']} / {lt['scored_on']}")],
            columns=["item", "value"])), "", plain_language(lt["probability"]), ""]
        
        if prof["status"] == "active":
            L += [f"**Suggested review action:** {RANK_ACTIONS[lt['priority_rank']]}", ""]
        else:
            L += ["This customer is recorded as churned; the score above was produced while they were active.", ""]
        
        L += ["### What moves this score (associations, not causes)", "",
              f"- Raising it: {factors_text(lt['risk_factors'])}",
              f"- Lowering it: {factors_text(lt['protective_factors'])}", "",
              "Each effect is the change in the model's estimate, in percentage points, compared with a typical customer."]
        
        L += [""]

    L += ["## Prediction history", ""]
    L += [md_table(rep["history"].tail(12)) if not rep["history"].empty else "No history.", ""]
    L += ["## Retention campaigns", ""]
    
    if rep["campaigns"]:
        camp = pd.DataFrame(rep["campaigns"]).astype(str)
        L += [md_table(camp), ""]
    else:
        L += ["Not enrolled in any campaign.", ""]
    
    return "\n".join(L)


def write_customer_reports(db: Session, customer_ids, directory) -> int:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written = 0
    
    for cid in customer_ids:
        rep = customer_report(db, cid)
        
        if rep:
            safe = re.sub(r"[^A-Za-z0-9_-]", "_", cid)
            (directory / f"{safe}.md").write_text(render_markdown(rep), encoding="utf-8")
            written += 1
    
    return written

