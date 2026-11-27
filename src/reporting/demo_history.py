"""
SYNTHETIC demo: add fake past scoring runs so the trend charts have something to show.
"""

import argparse
from datetime import timedelta, timezone

import numpy as np
from sqlalchemy import delete, func, select

from src.db.models import ChurnPrediction
from src.db.session import Base, SessionLocal, engine
from src.reporting.settings import SYNTHETIC_PREFIX



def main(months: int, drift: float, seed: int, cleanup: bool) -> None:
    Base.metadata.create_all(bind=engine)
    rng = np.random.default_rng(seed)
    with SessionLocal() as db:
        if cleanup:
            n = db.execute(delete(ChurnPrediction)
                           .where(ChurnPrediction.batch_id.like(SYNTHETIC_PREFIX + "%"))).rowcount
            db.commit()
            print(f"Removed {n:,} synthetic prediction rows.")
            return

        real = ~ChurnPrediction.batch_id.like(SYNTHETIC_PREFIX + "%")
        last_batch = db.scalar(select(ChurnPrediction.batch_id)
                               .where(ChurnPrediction.source == "batch", real)
                               .order_by(ChurnPrediction.prediction_id.desc()).limit(1))
        if last_batch is None:
            raise SystemExit("No stored batch predictions. Run: python -m src.ml.segment_run")
        
        base = db.scalars(select(ChurnPrediction).where(ChurnPrediction.batch_id == last_batch)).all()
        newest = max(r.prediction_date for r in base)
        
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=timezone.utc)

        # NEGATIVE ids guarantee that fake rows can never count as a customer's "latest" prediction
        next_id = min(db.scalar(select(func.min(ChurnPrediction.prediction_id))) or 0, 0) - 1
        rows = []

        for k in range(months, 0, -1):
            when = newest - timedelta(days=30 * k)
            batch = f"{SYNTHETIC_PREFIX}{when:%Y%m%dT%H%M%S}"
            for r in base:
                p = float(np.clip(r.probability - drift * k + rng.normal(0, 0.03), 0.001, 0.999))
                rows.append(ChurnPrediction(
                    prediction_id=next_id, customer_id=r.customer_id, batch_id=batch, source="batch",
                    model_version=r.model_version, probability=round(p, 4), threshold=r.threshold,
                    flagged_for_review=p >= r.threshold, risk_level=r.risk_level, value_tier=r.value_tier,
                    priority_segment=r.priority_segment, priority_rank=r.priority_rank,
                    top_risk_factors=None, top_protective_factors=None, prediction_date=when))
                next_id -= 1
        
        db.add_all(rows)
        db.commit()
        
        print(f"Added {len(rows):,} FAKE prediction rows in {months} synthetic batches (older runs are lower by "
              f"{drift:.0%} per month). Remove them with: python -m src.reporting.demo_history --cleanup")




if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=6)
    ap.add_argument("--drift", type=float, default=0.01, help="risk change per month (older = lower)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--cleanup", action="store_true", help="delete all synthetic rows")
    a = ap.parse_args()
    main(a.months, a.drift, a.seed, a.cleanup)

    