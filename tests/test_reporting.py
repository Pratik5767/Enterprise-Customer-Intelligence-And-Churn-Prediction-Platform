from datetime import date, datetime, timezone

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.analysis.prep import TENURE_BINS, TENURE_LABELS
from src.analysis.stats import churn_by
from src.db.models import CampaignActivity, ChurnPrediction, Customer, RetentionCampaign
from src.db.session import Base
from src.reporting import metrics as m, narrative as nar
from src.reporting.customer_report import customer_report, render_markdown
from src.reporting.data import load_history, load_portfolio
from src.reporting.exports import ReportFilter, apply_filters, export_frame, sanitize_for_csv



RISK = ["Low", "Medium", "High"]
FORBIDDEN = ["because", "caused", "causes", "causing", "driven by", "drives", "leads to", "due to"]


def make_portfolio() -> pd.DataFrame:
    cols = ["customer_id", "subscription_status", "tenure", "contract_type", "monthly_charges",
            "probability", "risk_level", "flagged_for_review", "priority_rank"]
    data = [("A1", "active", 2, "Month-to-month", 100.0, 0.80, "High", True, 1),
            ("A2", "active", 30, "One year", 50.0, 0.35, "Medium", False, 3),
            ("A3", "active", 60, "Two year", 20.0, 0.05, "Low", False, 4),
            ("A4", "active", 5, "Month-to-month", 80.0, 0.65, "High", True, 1),
            ("C1", "churned", 3, "Month-to-month", 90.0, None, None, False, None),
            ("C2", "churned", 40, "One year", 60.0, None, None, False, None)]
    
    df = pd.DataFrame(data, columns=cols)
    df["churn_flag"] = (df["subscription_status"] == "churned").astype(int)
    df["has_score"] = df["probability"].notna()
    df["value_tier"], df["priority_segment"], df["batch_id"] = "Mid value", "x", "batch-1"
    df["model_version"], df["internet_service"], df["payment_method"] = "v1", "DSL", "Mailed check"
    df["tenure_bucket"] = pd.cut(df["tenure"], bins=TENURE_BINS, labels=TENURE_LABELS)
    df["prediction_date"] = pd.Timestamp("2030-01-01", tz="UTC")
    
    return df


@pytest.fixture
def parts():
    return m.split_portfolio(make_portfolio(), 12)


def make_ctx(parts, trend=None):
    pf, active, scored = parts
    curve = m.concentration_curve(scored)
    
    return {
        "kpis": m.headline_kpis(pf, active, scored, RISK, 12),
        "contract": churn_by(pf, "contract_type"), 
        "tenure": churn_by(pf, "tenure_bucket"),
        "extra_churn": {
            "internet_service": churn_by(pf, "internet_service"),
            "payment_method": churn_by(pf, "payment_method")
        },
        "risk_tables": {
            "contract_type": m.risk_by_segment(scored, "contract_type", RISK)
        },
        "by_band": m.revenue_by_band(scored, RISK), 
        "priority": m.priority_table(scored),
        "concentration": {
            "top10": m.top_share(curve, 0.1), 
            "top20": m.top_share(curve, 0.2)
        },
        "trend": trend, 
        "movers": None, 
        "campaigns": pd.DataFrame(), 
        "campaign_claims": [],
        "risk_order": RISK, 
        "includes_synthetic": False
    }


# metrics
def test_headline_kpis(parts):
    pf, active, scored = parts
    k = m.headline_kpis(pf, active, scored, RISK, 12)
    assert (k["total_customers"], k["churned_customers"], k["retained_customers"]) == (6, 2, 4)
    assert k["churn_rate_pct"] == 33.3
    assert k["churned_billing_share_pct"] == 37.5            # 150 of 400
    assert k["high_band_customers"] == 2 and k["high_band_monthly_billing"] == 180.0
    assert k["flagged_for_review"] == 2
    assert k["expected_revenue_at_risk"] == pytest.approx(1806.0)   # 960 + 210 + 12 + 624


def test_revenue_by_band_shares(parts):
    band = m.revenue_by_band(parts[2], RISK).set_index("risk_level")
    assert band.loc["High", "customers_pct"] == 50.0
    assert band.loc["High", "expected_pct"] == 87.7
    assert band["expected_pct"].sum() == pytest.approx(100.0, abs=0.2)


def test_risk_by_segment(parts):
    t = m.risk_by_segment(parts[2], "contract_type", RISK).set_index("contract_type")
    assert t.loc["Month-to-month", "customers"] == 2
    assert t.loc["Month-to-month", "pct_high_risk"] == 100.0
    assert t.loc["Month-to-month", "pct_High"] == 100.0
    assert t.loc["One year", "pct_high_risk"] == 0.0


def test_concentration_curve(parts):
    curve = m.concentration_curve(parts[2])
    assert curve["loss_share"].iloc[-1] == pytest.approx(1.0)
    assert curve["loss_share"].is_monotonic_increasing
    assert m.top_share(curve, 0.25) == pytest.approx(960 / 1806)
    assert m.top_share(curve, 0.5) == pytest.approx(1584 / 1806)


def make_history() -> pd.DataFrame:
    rows = []
    for batch, date_, probs in [("b1", "2030-01-01", [0.5, 0.2]), ("b2", "2030-02-01", [0.7, 0.2])]:
        for cid, p in zip(["A1", "A2"], probs):
            rows.append({
                "prediction_id": len(rows) + 1, 
                "customer_id": cid, 
                "batch_id": batch,
                "model_version": "v1", 
                "probability": p, 
                "threshold": 0.5,
                "prediction_date": pd.Timestamp(date_, tz="UTC"), 
                "monthly_charges": 100.0
            })

    return pd.DataFrame(rows)


def test_trend_and_movers():
    h = make_history()
    t = m.risk_trend(h, 0.6, 12)
    assert t["batch_id"].tolist() == ["b1", "b2"]
    assert t["avg_probability"].tolist() == pytest.approx([0.35, 0.45])
    assert t["pct_high"].tolist() == [0.0, 50.0]
    mv = m.risk_movers(h)
    assert (mv["customers_compared"], mv["rose"], mv["fell"]) == (2, 1, 0)
    assert m.risk_movers(h[h["batch_id"] == "b1"]) is None       # one run: no movement to report


# filters and exports
def test_filters_are_validated_and_applied(parts):
    with pytest.raises(ValueError):
        ReportFilter(risk_levels=["Hihg"]).validate(RISK, ["Low value"])
    with pytest.raises(ValueError):
        ReportFilter(min_probability=0.9, max_probability=0.1).validate(RISK, ["Low value"])
    pf = parts[0]
    d = apply_filters(pf, ReportFilter(risk_levels=["High"], contract_types=["Month-to-month"]))
    assert d["customer_id"].tolist() == ["A1", "A4"]             # highest expected loss first
    assert apply_filters(pf, ReportFilter(statuses=["churned"], scored_only=False))["customer_id"].tolist() == ["C1", "C2"]


def test_export_has_no_sensitive_columns_and_neutralises_formulas(parts):
    out = export_frame(apply_filters(parts[0], ReportFilter()))
    assert "gender" not in out.columns and "churn_probability" in out.columns
    df = pd.DataFrame({"a": ["=SUM(A1:A9)", "ok", "-x", "@cmd"], "b": [1, 2, 3, 4]})
    assert sanitize_for_csv(df)["a"].tolist() == ["'=SUM(A1:A9)", "ok", "'-x", "'@cmd"]


# narrative
def test_summary_has_no_causal_wording(parts):
    s = nar.build_summary(make_ctx(parts))
    text = " ".join([s["headline"]] + s["findings"] + s["investigate"] + s["caveats"]).lower()
    assert not [w for w in FORBIDDEN if w in text]


def test_summary_states_when_trend_is_unavailable(parts):
    s = nar.build_summary(make_ctx(parts, trend=None))
    assert any("at least two" in f for f in s["findings"])
    s2 = nar.build_summary(make_ctx(parts, trend=m.risk_trend(make_history(), 0.6, 12)))
    assert any("moved from" in f for f in s2["findings"])


# database
@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


CUSTOMER = dict(
    gender="Male", senior_citizen="No", partner="No", dependents="No", 
    tenure=5, phone_service="Yes", multiple_lines="No", internet_service="DSL", 
    online_security="No", online_backup="No", device_protection="No", tech_support="No", 
    streaming_tv="No", streaming_movies="No", contract_type="Month-to-month", paperless_billing="Yes", 
    payment_method="Mailed check", monthly_charges=70.0, total_charges=350.0, subscription_start=date(2030, 1, 1),
    subscription_status="active", is_outlier=False
)


def prediction(cid, probability, batch, pid=None, source="batch", when=datetime(2030, 1, 2, tzinfo=timezone.utc)):
    kw = {"prediction_id": pid} if pid is not None else {}
    
    return ChurnPrediction(
        customer_id=cid, batch_id=batch, source=source, model_version="v1",
        probability=probability, threshold=0.5, flagged_for_review=probability >= 0.5,
        risk_level="High", value_tier="Mid value", priority_segment="Priority: mid value, high risk",
        priority_rank=2, 
        top_risk_factors=[{
            "factor": "Contract type", 
            "value": "Month-to-month",
            "effect_pct_points": 14.2
        }],
        top_protective_factors=[], 
        prediction_date=when, **kw
    )


def test_portfolio_keeps_churned_customers_and_ignores_fake_history(db):
    db.add_all([Customer(customer_id="X-1", **CUSTOMER),
                Customer(customer_id="X-2", **{**CUSTOMER, "subscription_status": "churned"})])
    db.add_all([prediction("X-1", 0.7, "batch-1"),
                prediction("X-1", 0.1, "synthetic-old", pid=-5, when=datetime(2029, 6, 1, tzinfo=timezone.utc))])
    db.commit()
    pf = load_portfolio(db).set_index("customer_id")
    assert len(pf) == 2                                          # the churned customer is NOT dropped
    assert bool(pf.loc["X-1", "has_score"]) and pf.loc["X-1", "probability"] == 0.7
    assert not bool(pf.loc["X-2", "has_score"]) and not bool(pf.loc["X-2", "flagged_for_review"])
    assert load_history(db)["batch_id"].nunique() == 1
    assert load_history(db, include_synthetic=True)["batch_id"].nunique() == 2


def test_customer_report_flags_holdout_customers(db):
    db.add(Customer(customer_id="X-1", **CUSTOMER))
    db.add(prediction("X-1", 0.7, "batch-1"))
    camp = RetentionCampaign(
        campaign_name="Spring calls", 
        campaign_type="phone_call", 
        target_segment="t",
        selection_rule={}, 
        owner="o", 
        status="active", 
        start_date=date(2030, 1, 1)
    )
    db.add(camp)
    db.flush()
    db.add(
        CampaignActivity(
            campaign_id=camp.campaign_id, customer_id="X-1", assignment="control",
            status="held_out", probability_at_enrollment=0.7, risk_level_at_enrollment="High",
            priority_segment_at_enrollment="x", priority_rank_at_enrollment=2,
            monthly_charges_at_enrollment=70.0, tenure_at_enrollment=5,
            contract_type_at_enrollment="Month-to-month"
        )
    )
    db.commit()
    rep = customer_report(db, "X-1")
    assert rep["do_not_contact"] == ["Spring calls"]
    text = render_markdown(rep)
    assert "DO NOT CONTACT" in text and "not a confirmed decision" in text
    assert customer_report(db, "NOPE") is None

    