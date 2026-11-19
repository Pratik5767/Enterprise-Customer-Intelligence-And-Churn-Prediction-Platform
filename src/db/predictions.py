from datetime import datetime

import pandas as pd
from sqlalchemy.exc import IntegrityError

from src.db.models import ChurnPrediction
from src.db.session import Base, SessionLocal, engine



def save_predictions(df: pd.DataFrame, batch_id: str, source: str = "batch") -> int:
    """
    Append one row per customer. Never updates or deletes earlier rows.
    """
    
    Base.metadata.create_all(bind=engine)           # creates churn_predictions if it doesn't exist yet
    
    rows = [
        ChurnPrediction(
            customer_id=r.customer_id, batch_id=batch_id, source=source,
            model_version=r.model_version, probability=float(r.churn_probability),
            threshold=float(r.threshold), flagged_for_review=bool(r.flagged_for_review),
            risk_level=str(r.risk_level), value_tier=str(r.value_tier),
            priority_segment=str(r.priority_segment), priority_rank=int(r.priority_rank),
            top_risk_factors=r.top_risk_factors, top_protective_factors=r.top_protective_factors,
            prediction_date=datetime.fromisoformat(r.prediction_date),
        ) 
        for r in df.itertuples(index=False)
    ]

    with SessionLocal() as session:
        try:
            session.add_all(rows)
            session.commit()
        except IntegrityError as e:
            session.rollback()
            raise RuntimeError(
                "Could not store predictions. Are the customers loaded? "
                "Run: python -m src.ingestion.pipeline"
            ) from e
    
    return len(rows)

