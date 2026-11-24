from datetime import date, timedelta
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.campaigns import analysis as an
from src.campaigns.selection import apply_rule, assign_groups, assign_reps
from src.campaigns.service import (CampaignError, CampaignSpec, create_campaign, follow_up_queue,
                                   launch_campaign, log_outreach, record_retention_outcome)
from src.db.models import CampaignActivity, RetentionCampaign
from src.db.session import Base



@pytest.fixture
def db():
    engine = create_engine("sqlite://")              # throwaway in-memory database
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_selected(n=100, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    even = np.arange(n) % 2 == 0
    df = pd.DataFrame({
        "prediction_id": np.arange(1, n + 1), 
        "customer_id": [f"C{i:04d}" for i in range(n)],
        "probability": rng.uniform(0.3, 0.9, n).round(3), 
        "risk_level": "High", 
        "value_tier": "Mid value",
        "priority_segment": np.where(even, "Critical: high value, high risk", "Priority: mid value, high risk"),
        "priority_rank": np.where(even, 1, 2), 
        "monthly_charges": rng.uniform(40, 110, n).round(2),
        "tenure": rng.integers(1, 72, n), 
        "contract_type": "Month-to-month", 
        "flagged_for_review": True
    })
    df["expected_revenue_at_risk"] = (df["probability"] * df["monthly_charges"] * 12).round(2)
    return df


def spec(**kw) -> CampaignSpec:
    base = dict(
        name="Test campaign", 
        campaign_type="phone_call", 
        owner="owner@example.com",
        reps=["rep1", "rep2", "rep3"], 
        start_date=date(2030, 1, 1), 
        target_segment="test",
        selection_rule={}, 
        holdout_share=0.2, 
        cost_per_contact=30.0, 
        incentive_cost=20.0
    )
    base.update(kw)
    return CampaignSpec(**base)


def outcomes_df(t_retained, t_total, c_retained, c_total) -> pd.DataFrame:
    rows = []
    for group, k, n in (("treatment", t_retained, t_total), ("control", c_retained, c_total)):
        rows += [{"assignment": group, "retention_outcome": "retained" if i < k else "churned"} for i in range(n)]
    return pd.DataFrame(rows, columns=["assignment", "retention_outcome"])


# selection
def test_apply_rule_filters_and_rejects_unknown_keys():
    sel = make_selected()
    assert set(apply_rule(sel, {"priority_ranks": [1]})["priority_rank"]) == {1}
    assert len(apply_rule(sel, {"max_customers": 10})) == 10
    with pytest.raises(ValueError):
        apply_rule(sel, {"priority_rank": [1]})                     # typo: the key is priority_ranks


def test_holdout_is_random_balanced_and_reproducible():
    sel = make_selected()
    g1, g2, g3 = (assign_groups(sel, 0.2, seed=s) for s in (1, 1, 2))
    assert g1.equals(g2) and not g1.equals(g3)
    assert (g1 == "control").sum() == 20
    for _, idx in sel.groupby("priority_segment").groups.items():
        assert (g1.loc[idx] == "control").sum() == 10               # same share inside every segment


def test_reps_get_even_workloads_and_capacity_is_enforced():
    treat = make_selected(31)
    counts = assign_reps(treat, ["a", "b", "c"]).value_counts()
    assert counts.max() - counts.min() <= 1
    with pytest.raises(ValueError):
        assign_reps(treat, ["a", "b"], max_per_rep=10)


# workflow
def test_create_campaign_enrolls_treatment_and_holdout(db):
    out = create_campaign(db, spec(), make_selected())
    assert (out["enrolled"], out["treatment"], out["control"]) == (100, 80, 20)
    acts = db.scalars(select(CampaignActivity)).all()
    held = [a for a in acts if a.assignment == "control"]
    assert all(a.status == "held_out" and a.assigned_to is None and a.follow_up_date is None for a in held)
    treat = [a for a in acts if a.assignment == "treatment"]
    assert all(
        a.status == "pending" and a.assigned_to in {"rep1", "rep2", "rep3"} and a.follow_up_date >= date(2030, 1, 3) 
        for a in treat
    )


def test_campaign_rules_are_enforced(db):
    create_campaign(db, spec(), make_selected())
    with pytest.raises(CampaignError):                              # same name
        create_campaign(db, spec(), make_selected())
    with pytest.raises(CampaignError):                              # customers already in an open campaign
        create_campaign(db, spec(name="Other"), make_selected())
    with pytest.raises(CampaignError):                              # unknown campaign type
        create_campaign(db, spec(name="Third", campaign_type="carrier_pigeon"), make_selected())


def test_holdout_customers_cannot_be_contacted(db):
    cid = create_campaign(db, spec(), make_selected())["campaign_id"]
    launch_campaign(db, cid)
    control = db.scalars(select(CampaignActivity).where(CampaignActivity.assignment == "control")).first()
    with pytest.raises(CampaignError, match="control"):
        log_outreach(db, control.activity_id, reached=True, outcome="accepted_offer")


def test_outreach_workflow_and_costs(db):
    cid = create_campaign(db, spec(), make_selected())["campaign_id"]
    treat = db.scalars(select(CampaignActivity).where(CampaignActivity.assignment == "treatment")).all()
    a_id, b_id = treat[0].activity_id, treat[1].activity_id
    with pytest.raises(CampaignError):                              # campaign not launched yet
        log_outreach(db, a_id, reached=False)
    launch_campaign(db, cid)

    on = date(2030, 1, 4)
    r = log_outreach(db, a_id, reached=False, on=on)
    assert r["status"] == "attempted" and r["follow_up_date"] == on + timedelta(days=2)
    log_outreach(db, a_id, reached=False, on=on)
    r = log_outreach(db, a_id, reached=False, on=on)
    assert r["status"] == "unreachable" and r["follow_up_date"] is None
    with pytest.raises(CampaignError):                              # unreachable customers are closed to contact
        log_outreach(db, a_id, reached=True, outcome="accepted_offer")

    assert log_outreach(db, b_id, reached=True, outcome="accepted_offer", on=on)["status"] == "contacted"
    with pytest.raises(CampaignError):                              # a reached customer needs an outcome
        log_outreach(db, b_id, reached=True)

    costs = an.campaign_costs(an.load_activities(db, cid), db.get(RetentionCampaign, cid))
    assert costs["contact_cost"] == 4 * 30.0                        # 3 attempts on A + 1 on B
    assert costs["incentive_cost"] == 20.0                          # one accepted offer


def test_retention_outcome_is_recorded_once_for_both_groups(db):
    cid = create_campaign(db, spec(), make_selected())["campaign_id"]
    launch_campaign(db, cid)
    control = db.scalars(select(CampaignActivity).where(CampaignActivity.assignment == "control")).first()
    record_retention_outcome(db, control.activity_id, retained=True)
    with pytest.raises(CampaignError):
        record_retention_outcome(db, control.activity_id, retained=False)
    record_retention_outcome(db, control.activity_id, retained=False, overwrite=True)


def test_follow_up_queue_lists_open_work_with_overdue_first(db):
    cid = create_campaign(db, spec(), make_selected())["campaign_id"]
    launch_campaign(db, cid)
    q = follow_up_queue(db, "rep1", as_of=date(2030, 1, 4))
    assert len(q) > 0 and q["overdue"].any()                        # rank-1 customers were due on Jan 3
    assert bool(q.loc[0, "overdue"])


# evidence
def test_minimum_detectable_effect():
    assert an.minimum_detectable_effect(0.5, 1000, 1000) == pytest.approx(0.0626, abs=0.001)


def test_clear_randomised_effect_is_attributed_to_the_campaign():
    res = an.compare_groups(outcomes_df(720, 1000, 160, 250), SimpleNamespace(holdout_share=0.2))
    assert res["computable"] and res["difference_pts"] == pytest.approx(8.0)
    assert 0 < res["ci_low_pts"] < 8.0 < res["ci_high_pts"]
    assert "attributed to the campaign" in an.claim_text(res)


def test_uncertain_effect_is_not_claimed():
    res = an.compare_groups(outcomes_df(700, 1000, 160, 250), SimpleNamespace(holdout_share=0.2))
    assert res["ci_low_pts"] < 0 < res["ci_high_pts"]
    assert "do not show" in an.claim_text(res)


def test_without_a_control_group_no_effect_is_claimed():
    res = an.compare_groups(outcomes_df(700, 1000, 0, 0), SimpleNamespace(holdout_share=0.0))
    assert not res["computable"]
    assert "cannot" in an.claim_text(res).lower()


def test_low_outcome_coverage_is_flagged():
    df = outcomes_df(720, 1000, 160, 250)
    df.loc[df.index[:600], "retention_outcome"] = np.nan            # 60% of the campaign group's outcomes missing
    res = an.compare_groups(df, SimpleNamespace(holdout_share=0.2))
    assert any("coverage" in w.lower() for w in res["warnings"])


def test_economics_arithmetic():
    res = {"computable": True, "difference_pts": 8.0, "ci_low_pts": 1.7, "ci_high_pts": 14.7}
    e = an.economics(res, n_treatment=1000, avg_annual_value=600.0, total_cost=30000.0)
    assert e["additional_retained"] == pytest.approx(80)
    assert e["net_benefit"] == pytest.approx(18000)
    assert e["net_low"] == pytest.approx(17 * 600 - 30000)
    assert e["cost_per_additional_retained"] == pytest.approx(375)
    assert an.economics({"computable": False}, 1000, 600.0, 30000.0) is None

