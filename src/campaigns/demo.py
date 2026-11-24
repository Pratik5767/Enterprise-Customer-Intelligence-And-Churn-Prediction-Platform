"""
SYNTHETIC demo: create a campaign, simulate outreach and outcomes, build the report.
"""

import argparse
from datetime import date, datetime

import numpy as np

from src.campaigns.analysis import load_activities
from src.campaigns.constants import MAX_ATTEMPTS, OUTCOMES
from src.campaigns.report import CAMPAIGN_DIR, build_report, campaign_overview
from src.campaigns.selection import preview, select_customers
from src.campaigns.service import (CampaignSpec, complete_campaign, create_campaign,
                                   delete_synthetic_campaigns, launch_campaign, log_outreach,
                                   record_retention_outcome)
from src.db.session import Base, SessionLocal, engine



def simulate(db, campaign_id: int, effect: float, seed: int) -> None:
    rng = np.random.default_rng(seed)
    for r in load_activities(db, campaign_id).itertuples():
        p = float(r.probability_at_enrollment)
        reached = False
        if r.assignment == "treatment":
            reach_prob = float(np.clip(0.85 - 0.6 * p, 0.15, 0.85))      # riskier customers are harder to reach
            for _ in range(MAX_ATTEMPTS):
                if rng.random() < reach_prob:
                    outcome = str(rng.choice(OUTCOMES, p=[0.35, 0.25, 0.10, 0.30]))
                    log_outreach(db, int(r.activity_id), reached=True, outcome=outcome, commit=False)
                    reached = True
                    break
                log_outreach(db, int(r.activity_id), reached=False, commit=False)
        churn_prob = p * (1 - effect) if reached else p                  # the planted truth
        record_retention_outcome(db, int(r.activity_id), retained=bool(rng.random() >= churn_prob), commit=False)
    db.commit()


def main(effect: float, holdout: float, seed: int, cleanup: bool) -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if cleanup:
            print(f"Removed {delete_synthetic_campaigns(db)} synthetic demo campaign(s).")
            return

        rule = {"priority_ranks": [1, 2]}                                 # Critical + Priority segments (Module 4)
        info = preview(db, rule, holdout)
        print("Preview:", info)
        if info["matching_customers"] < 40:
            raise SystemExit("Too few customers match. Widen the rule, e.g. priority_ranks [1, 2, 3].")

        selected = select_customers(db, rule)
        spec = CampaignSpec(
            name=f"[SYNTHETIC DEMO] Retention calls {datetime.now():%Y%m%d-%H%M%S}",
            campaign_type="phone_call", owner="demo.manager@example.com",
            reps=["rep.asha@example.com", "rep.rahul@example.com", "rep.neha@example.com"],
            start_date=date.today(), target_segment="Critical and Priority customers (Module 4 ranks 1-2)",
            selection_rule=rule, holdout_share=holdout, cost_per_contact=30.0, incentive_cost=25.0,
            seed=seed, is_synthetic=True
        )
        made = create_campaign(db, spec, selected)
        cid = made["campaign_id"]
        print("Created:", made)
        launch_campaign(db, cid)

        simulate(db, cid, effect, seed)
        t = load_activities(db, cid).query("assignment == 'treatment'")
        planted = 100 * float((t["probability_at_enrollment"] * effect * t["outcome"].notna()).mean())
        print(f"Planted effect (expected difference in retention, assigned vs holdout): about {planted:.1f} points")

        print("Completed:", complete_campaign(db, cid))
        print("Report:", build_report(db, cid))
        print(campaign_overview(db).to_string(index=False))
        print(f"\nOpen {CAMPAIGN_DIR / f'campaign_{cid}.md'} and compare its section 5 with the planted effect above.")



if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--effect", type=float, default=0.5, help="relative churn reduction for reached customers")
    ap.add_argument("--holdout", type=float, default=0.25)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--cleanup", action="store_true", help="delete all synthetic demo campaigns")
    a = ap.parse_args()
    main(a.effect, a.holdout, a.seed, a.cleanup)

