import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from src.config import ALLOWED_VALUES
from src.ml import business
from src.ml.pipeline import add_engineered_features, build_pipeline
from src.ml.settings import CATEGORICAL_FEATURES, EXCLUDED_SENSITIVE, INPUT_FEATURES, LEAKAGE_COLUMNS, MODEL_VERSION, MODELS_DIR



MODEL_FILE = MODELS_DIR / f"churn_pipeline_{MODEL_VERSION}.joblib"


def fake_customers(n=300, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "tenure": rng.integers(0, 73, n),
        "monthly_charges": rng.uniform(20, 110, n).round(2)    
    })
    df["total_charges"] = (df["tenure"] * df["monthly_charges"]).round(2)
    for col in CATEGORICAL_FEATURES:
        options = ["No", "Yes"] if col == "senior_citizen" else sorted(ALLOWED_VALUES[col])
        df[col] = rng.choice(options, n)
    return df


def test_no_leakage_columns_in_features():
    assert not set(INPUT_FEATURES) & set(LEAKAGE_COLUMNS)


def test_sensitive_columns_not_used_as_inputs():
    assert not set(INPUT_FEATURES) & set(EXCLUDED_SENSITIVE)


def test_engineered_features():
    rec = fake_customers(1, seed=1).iloc[0].to_dict()
    rec.update(
        phone_service="Yes", 
        internet_service="DSL", 
        online_security="Yes",
        online_backup="No", 
        device_protection="No", 
        tech_support="No",
        streaming_tv="No", 
        streaming_movies="No", 
        monthly_charges=60.0
    )
    out = add_engineered_features(pd.DataFrame([rec])).iloc[0]
    assert out["num_addons"] == 1
    assert out["num_services"] == 3                 # phone + internet + 1 add-on
    assert out["charges_per_service"] == 20.0


def test_pipeline_scores_new_record_and_tolerates_unseen_category():
    X = fake_customers(300, seed=0)
    y = np.random.default_rng(0).integers(0, 2, 300)
    pipe = build_pipeline(LogisticRegression(max_iter=500)).fit(X, y)
    rec = fake_customers(1, seed=5)
    rec.loc[0, "contract_type"] = "Weekly"          # never seen in training
    p = pipe.predict_proba(rec)[0, 1]
    assert 0.0 <= p <= 1.0


def test_business_outcome_arithmetic():
    out = business.business_outcome(
        y_true=[1, 1, 0, 0], proba=[0.9, 0.4, 0.8, 0.1], value=[100, 200, 300, 400],
        threshold=0.5, contact_cost=10, success_rate=0.25)
    assert out["contacted"] == 2
    assert (out["true_positives"], out["false_positives"], out["false_negatives"]) == (1, 1, 1)
    assert out["revenue_saved"] == 25               # 0.25 x 100
    assert out["campaign_cost"] == 20
    assert out["net_benefit"] == 5
    assert out["missed_churn_value"] == 200
    assert out["wasted_contact_cost"] == 10


def test_choose_threshold_respects_capacity():
    rng = np.random.default_rng(0)
    proba = rng.uniform(size=1000)
    y = rng.binomial(1, proba)
    table = business.threshold_table(y, proba, np.full(1000, 500.0))
    t = business.choose_threshold(table, capacity_share=0.2)
    assert (proba >= t).mean() <= 0.2


@pytest.mark.skipif(not MODEL_FILE.exists(), reason="train first: python -m src.ml.train")
def test_saved_model_scores_a_new_record():
    from src.ml.predict import predict_churn
    out = predict_churn(fake_customers(1).iloc[0].to_dict())
    assert 0.0 <= out["churn_probability"] <= 1.0
    assert out["model_version"] == MODEL_VERSION and out["prediction_date"]

