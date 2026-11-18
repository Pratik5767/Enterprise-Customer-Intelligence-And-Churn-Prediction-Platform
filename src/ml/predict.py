import json
from datetime import datetime, timezone
from functools import lru_cache

import joblib
import pandas as pd

from src.ml.settings import INPUT_FEATURES, MODEL_VERSION, MODELS_DIR



@lru_cache(maxsize=4)
def load_model(version: str = MODEL_VERSION):
    """Load once and keep in memory (important for the API: don't reload on every request)."""
    
    model = joblib.load(MODELS_DIR / f"churn_pipeline_{version}.joblib")
    meta = json.loads((MODELS_DIR / f"model_metadata_{version}.json").read_text())
    return model, meta


def _inputs(records) -> pd.DataFrame:
    df = pd.DataFrame(records)
    missing = [c for c in INPUT_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    return df[INPUT_FEATURES]          # extra keys (customer_id, gender, ...) are ignored


def predict_batch(records, version: str = MODEL_VERSION, threshold: float | None = None) -> pd.DataFrame:
    model, meta = load_model(version)
    thr = meta["threshold"] if threshold is None else threshold
    X = _inputs(records)
    proba = model.predict_proba(X)[:, 1]
    out = pd.DataFrame({"churn_probability": proba.round(4), "predicted_churn": proba >= thr},
                       index=X.index)
    out["threshold"] = thr
    out["model_version"] = version
    out["prediction_date"] = datetime.now(timezone.utc).isoformat()
    return out


def predict_churn(record: dict, version: str = MODEL_VERSION, threshold: float | None = None) -> dict:
    r = predict_batch([record], version, threshold).iloc[0]
    return {"customer_id": record.get("customer_id"),
            "churn_probability": float(r["churn_probability"]),
            "predicted_churn": bool(r["predicted_churn"]),
            "threshold": float(r["threshold"]),
            "model_version": r["model_version"],
            "prediction_date": r["prediction_date"]}

