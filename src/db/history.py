import pandas as pd
from sqlalchemy import text

from src.db.session import engine



def _query(sql: str, **params) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def customer_history(customer_id: str) -> pd.DataFrame:
    """
    Every prediction ever stored for one customer, oldest first.
    """
    
    return _query("""
        SELECT 
            prediction_date, 
            batch_id, 
            model_version, 
            probability, 
            risk_level,
            priority_segment, 
            flagged_for_review
        FROM churn_predictions WHERE customer_id = :cid
        ORDER BY prediction_date, prediction_id
    """, cid=customer_id)


def latest_scores() -> pd.DataFrame:
    """The most recent prediction for each customer."""
    
    return _query("""
        SELECT 
            p.* 
        FROM churn_predictions p
        JOIN (
            SELECT 
                customer_id, 
                MAX(prediction_id) AS last_id
            FROM churn_predictions 
            WHERE customer_id IS NOT NULL 
            GROUP BY customer_id
        ) m
        ON p.prediction_id = m.last_id
    """)


def risk_changes(old_batch: str, new_batch: str) -> pd.DataFrame:
    """How each customer's risk moved between two scoring runs (largest increase first)."""
    
    return _query("""
        SELECT 
            n.customer_id, 
            o.risk_level AS old_risk, 
            n.risk_level AS new_risk,
            o.probability AS old_probability, 
            n.probability AS new_probability,
            n.probability - o.probability AS change
        FROM churn_predictions n
        JOIN churn_predictions o ON o.customer_id = n.customer_id
        WHERE o.batch_id = :old AND n.batch_id = :new
        ORDER BY change DESC
    """, old=old_batch, new=new_batch)

