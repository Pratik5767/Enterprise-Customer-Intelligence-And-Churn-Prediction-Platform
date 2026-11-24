import json
from datetime import timedelta

import pandas as pd
import plotly.express as px
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analysis.charts import save
from src.analysis.run_eda import md_table
from src.campaigns.analysis import analyse, campaign_costs, load_activities, participation
from src.config import REPORTS_DIR
from src.db.models import RetentionCampaign



CAMPAIGN_DIR = REPORTS_DIR / "campaigns"


def _pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _kv(pairs) -> str:
    return md_table(pd.DataFrame([{"item": k, "value": v} for k, v in pairs]))


def build_report(db: Session, campaign_id: int):
    a = analyse(db, campaign_id)
    c, p, k, cmp_, econ = a["campaign"], a["participation"], a["costs"], a["comparison"], a["economics"]
    CAMPAIGN_DIR.mkdir(parents=True, exist_ok=True)
    due = c.start_date + timedelta(days=c.outcome_window_days)

    L = [f"# Retention Campaign Report: {c.campaign_name}", ""]
    if c.is_synthetic:
        L += ["> **SYNTHETIC DEMO DATA.** Outreach and retention outcomes below were simulated to test the "
              "software. They are not real results.", ""]
    
    L += ["## 1. Campaign", "", _kv([
        ("Type", c.campaign_type), ("Owner", c.owner), ("Status", c.status),
        ("Target segment", c.target_segment), ("Selection rule", json.dumps(c.selection_rule)),
        ("Start date", c.start_date), ("Retention outcomes due from", due),
        ("Design", cmp_["design"]), ("Holdout share", f"{c.holdout_share:.0%}"),
        ("Cost per contact attempt", c.cost_per_contact), ("Incentive cost per accepted offer", c.incentive_cost),
        ("Fixed cost", c.fixed_cost)]), "",
        "## 2. Outreach and participation", "", _kv([
            ("Customers enrolled", p["enrolled"]), ("In the campaign group", p["treatment"]),
            ("In the holdout (not contacted)", p["control"]), ("Contact attempted", p["attempted"]),
            ("Reached", p["reached"]), ("Reach rate (reached / attempted)", _pct(p["reach_rate"])),
            ("Unreachable after repeated attempts", p["unreachable"]), ("Not yet contacted", p["still_pending"]),
            ("Overdue follow-ups", p["overdue_follow_ups"]), ("Offers accepted", p["offers_accepted"]),
            ("Acceptance rate (accepted / reached)", _pct(p["acceptance_rate"])), ("Declined", p["declined"])]), "",
        "## 3. Costs", "", _kv([
            ("Contact attempts", k["contact_attempts"]), ("Contact cost", k["contact_cost"]),
            ("Incentive cost", k["incentive_cost"]), ("Fixed cost", k["fixed_cost"]),
            ("**Total cost**", k["total_cost"]),
            ("Variable cost per customer reached", k["variable_cost_per_customer_reached"])]), ""]

    L += ["## 4. Retention outcomes by group", ""]
    L += [md_table(a["retention"]) if not a["retention"].empty else "No retention outcomes recorded yet.", ""]

    L += ["## 5. What can and cannot be concluded", "", f"**{cmp_['claim']}**", ""]
    L += [f"- Warning: {w}" for w in cmp_.get("warnings", [])]
    L += ["- This is measured per customer *assigned*, including those who could not be reached.",
          "- One campaign in one period is one experiment; repeat it before treating the result as general.", ""]

    L += ["## 6. Money impact", ""]
    if econ:
        L += [_kv([
            ("Additional customers retained (estimate)",
             f"{econ['additional_retained']:.1f} (95% CI {econ['additional_retained_low']:.1f} to "
             f"{econ['additional_retained_high']:.1f})"),
            ("Incremental revenue (estimate)", f"{econ['incremental_revenue']:,.0f}"),
            ("Total campaign cost", f"{econ['total_cost']:,.0f}"),
            ("Net benefit (estimate)",
             f"{econ['net_benefit']:,.0f} (range {econ['net_low']:,.0f} to {econ['net_high']:,.0f})"),
            ("Return on cost", "n/a" if econ["roi"] is None else f"{econ['roi']:.0%}"),
            ("Cost per additional customer retained",
             "n/a (no estimated gain)" if econ["cost_per_additional_retained"] is None
             else f"{econ['cost_per_additional_retained']:,.0f}")]), "",
            f"Assumptions: a retained customer is worth {c.value_horizon_months} months of their monthly charges; "
            "customers with unknown outcomes behave like those with known outcomes. If the range includes "
            "negative values, the campaign may not have paid for itself.", ""]
    else:
        L += ["Not computed. Money impact is only estimated from a randomised comparison; without one, the "
              "observed costs in section 3 are all that can be reported.", ""]

    L += ["## 7. Were the groups alike at the start? (randomisation check)", ""]
    L += [md_table(a["balance"]) if not a["balance"].empty else "Not available (needs both groups).", "",
          "SMD values above about 0.1 in absolute size mean the groups differ at enrolment.", ""]

    L += ["## 8. Reached vs not reached (descriptive only, not an effect estimate)", ""]
    if not a["reached_vs_not"].empty:
        L += [md_table(a["reached_vs_not"]), "",
              "Compare the starting risk of the two rows. Customers who can be reached are usually "
              "different from those who cannot, so a gap in retention here mixes the campaign with that "
              "difference. Use section 5 for any statement about the campaign's effect.", ""]
    else:
        L += ["No outcomes recorded yet.", ""]

    L += ["## 9. By priority segment (exploratory)", ""]
    L += [md_table(a["by_segment"]) if not a["by_segment"].empty else "No outcomes recorded yet.", "",
          "Subgroups are small and many were examined; do not act on a single subgroup result.", ""]
    path = CAMPAIGN_DIR / f"campaign_{campaign_id}.md"
    path.write_text("\n".join(L), encoding="utf-8")
    a["df"].to_csv(CAMPAIGN_DIR / f"campaign_{campaign_id}_activities.csv", index=False)

    ret = a["retention"]
    if not ret.empty and ret["outcomes_known"].sum() > 0:
        fig = px.bar(ret, x="group", y="retention_rate_pct", text="retention_rate_pct",
                     error_y=ret["ci_high_pct"] - ret["retention_rate_pct"],
                     error_y_minus=ret["retention_rate_pct"] - ret["ci_low_pct"],
                     title=f"Retention rate by group (95% CI): {c.campaign_name}",
                     labels={"retention_rate_pct": "Retention rate (%)", "group": ""})
        save(fig, f"campaign_{campaign_id}_retention", CAMPAIGN_DIR)
    
    return path


def campaign_overview(db: Session) -> pd.DataFrame:
    rows = []
    
    for camp in db.scalars(select(RetentionCampaign).order_by(RetentionCampaign.campaign_id)).all():
        df = load_activities(db, camp.campaign_id)
        part, cost = participation(df), campaign_costs(df, camp)
        rows.append({
            "campaign_id": camp.campaign_id, 
            "name": camp.campaign_name, 
            "type": camp.campaign_type,
            "owner": camp.owner, 
            "status": camp.status, 
            "synthetic": camp.is_synthetic,
            "enrolled": part["enrolled"], "treatment": part["treatment"], "control": part["control"],
            "reach_rate_pct": None if part["reach_rate"] is None else round(100 * part["reach_rate"], 1),
            "offers_accepted": part["offers_accepted"], "total_cost": cost["total_cost"]
        })
    
    out = pd.DataFrame(rows)
    CAMPAIGN_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(CAMPAIGN_DIR / "campaign_overview.csv", index=False)
    
    return out

