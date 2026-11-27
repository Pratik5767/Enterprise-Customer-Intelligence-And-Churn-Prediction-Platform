import json

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.analysis.prep import TENURE_BINS, TENURE_LABELS
from src.ml.settings import MODEL_VERSION, MODELS_DIR
from src.reporting.settings import SYNTHETIC_PREFIX



# ALL customers (so churned ones count too), each with the latest BATCH prediction if one exists.
# Fake demo history (synthetic-...) is never used for the current snapshot.
PORTFOLIO_SQL = """
    SELECT 
        c.customer_id, c.tenure, c.contract_type, c.internet_service, c.payment_method,
        c.monthly_charges, c.total_charges, c.subscription_status,
        p.prediction_id, p.batch_id, p.model_version, p.probability, p.threshold,
        p.flagged_for_review, p.risk_level, p.value_tier, p.priority_segment, p.priority_rank,
        p.prediction_date
    FROM customers c 
    LEFT JOIN (
        SELECT q.* 
        FROM churn_predictions q 
        JOIN (
            SELECT 
                customer_id, 
                MAX(prediction_id) AS last_id
            FROM churn_predictions
            WHERE customer_id IS NOT NULL AND source = 'batch' AND batch_id NOT LIKE :synthetic
            GROUP BY customer_id
        ) m
        ON q.prediction_id = m.last_id
    ) p ON p.customer_id = c.customer_id
"""

HISTORY_SQL = """
    SELECT 
        p.prediction_id, p.customer_id, p.batch_id, 
        p.model_version, p.probability, p.threshold,
        p.prediction_date, c.monthly_charges
    FROM churn_predictions p
    JOIN customers c ON c.customer_id = p.customer_id
    WHERE p.source = 'batch'
"""


def load_model_meta() -> dict:
    path = MODELS_DIR / f"model_metadata_{MODEL_VERSION}.json"
    if not path.exists():
        raise FileNotFoundError("Train the model first: python -m src.ml.train")
    return json.loads(path.read_text())


def load_portfolio(db: Session) -> pd.DataFrame:
    df = pd.read_sql(
        text(PORTFOLIO_SQL), 
        db.connection(), 
        params={"synthetic": SYNTHETIC_PREFIX + "%"}
    )
    df["churn_flag"] = (df["subscription_status"] == "churned").astype(int)
    df["tenure_bucket"] = pd.cut(df["tenure"], bins=TENURE_BINS, labels=TENURE_LABELS)
    df["has_score"] = df["probability"].notna()
    df["flagged_for_review"] = df["flagged_for_review"].fillna(0).astype(int).astype(bool)
    df["prediction_date"] = pd.to_datetime(df["prediction_date"], utc=True, errors="coerce")
    return df


def load_history(db: Session, include_synthetic: bool = False) -> pd.DataFrame:
    """
    Every stored batch prediction (one row per customer per scoring run), for trend analysis.
    """
    
    sql, params = HISTORY_SQL, {}
    if not include_synthetic:
        sql += " AND p.batch_id NOT LIKE :synthetic"
        params = {"synthetic": SYNTHETIC_PREFIX + "%"}
    df = pd.read_sql(text(sql), db.connection(), params=params)
    df["prediction_date"] = pd.to_datetime(df["prediction_date"], utc=True, errors="coerce")
    return df

