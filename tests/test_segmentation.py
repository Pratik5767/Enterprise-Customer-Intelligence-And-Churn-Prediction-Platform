import numpy as np
import pandas as pd
import pytest

from src.ml import segmentation as seg
from src.ml.explain import FACTOR_GROUPS, explain_batch
from src.ml.settings import INPUT_FEATURES, NUMERIC_FEATURES



CFG = seg.DEFAULT_CONFIG


def test_default_config_is_valid():
    seg.validate_config(CFG)


def test_missing_matrix_entry_is_caught():
    bad = {
        **CFG, 
        "priority_matrix": {
            k: v for k, v in CFG["priority_matrix"].items()
            if k != "High|High value"
        }
    }
    with pytest.raises(ValueError):
        seg.validate_config(bad)


def test_risk_band_boundaries():
    p = pd.Series([0.0, 0.29, 0.30, 0.59, 0.60, 1.0])
    assert seg.assign_bands(p, CFG["risk_bands"]).astype(str).tolist() == [
        "Low", "Low", "Medium", "Medium", "High", "High"
    ]


def test_bands_are_configurable():
    assert seg.assign_bands(pd.Series([0.2, 0.5]), {"Safe": 0.0, "Risky": 0.4}).astype(str).tolist() == [
        "Safe", "Risky"]


def customer(**kw):
    base = dict(phone_service="Yes", internet_service="DSL", online_security="Yes", online_backup="No",
                device_protection="No", tech_support="No", streaming_tv="No", streaming_movies="No",
                monthly_charges=100.0, tenure=5, contract_type="Month-to-month")
    base.update(kw)
    return base


def test_build_segments_combines_risk_and_value():
    raw = pd.DataFrame([customer(monthly_charges=100.0), customer(monthly_charges=30.0, tenure=60)])
    cutoffs = {"value_tiers": {"Low value": 0.0, "Mid value": 50.0, "High value": 80.0}}
    out = seg.build_segments(raw, [0.8, 0.1], CFG, cutoffs, horizon_months=12)
    
    assert out.loc[0, "priority_segment"].startswith("Critical") and out.loc[0, "priority_rank"] == 1
    assert out.loc[0, "annual_value"] == 1200.0
    assert out.loc[0, "expected_revenue_at_risk"] == 960.0
    assert out.loc[1, "risk_level"] == "Low" and out.loc[1, "value_tier"] == "Low value"
    assert str(out.loc[1, "tenure_segment"]).startswith("Loyal")


def test_plain_language_is_a_likelihood_not_a_decision():
    text = seg.plain_language(0.30)
    assert "30 in 100" in text and "not a decision" in text


def test_factor_groups_cover_every_model_input_exactly_once():
    cols = [c for group_cols, _ in FACTOR_GROUPS.values() for c in group_cols]
    assert sorted(cols) == sorted(INPUT_FEATURES)


class StubModel:
    """Risk is 0.6 for month-to-month customers and 0.2 otherwise."""
    def predict_proba(self, X):
        p = np.where(X["contract_type"] == "Month-to-month", 0.6, 0.2)
        return np.column_stack([1 - p, p])


def dummy_row(**kw):
    row = {c: (0.0 if c in NUMERIC_FEATURES else "x") for c in INPUT_FEATURES}
    row.update(kw)
    return row


def test_explanation_finds_the_factor_that_moves_the_probability():
    reference = dummy_row(contract_type="Two year")
    X = pd.DataFrame([dummy_row(contract_type="Month-to-month"), dummy_row(contract_type="Two year")])
    out = explain_batch(StubModel(), X, reference)
    top = out.loc[0, "top_risk_factors"]
    assert top[0]["factor"] == "Contract type" and top[0]["effect_pct_points"] == 40.0
    assert out.loc[0, "top_protective_factors"] == []
    assert out.loc[1, "top_risk_factors"] == [] and out.loc[1, "top_protective_factors"] == []