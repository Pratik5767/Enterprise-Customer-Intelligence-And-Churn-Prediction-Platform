"""
Score active customers, assign risk/value segments, explain each prediction, store history.
"""

import argparse
from datetime import datetime, timezone

import pandas as pd

from src.config import PROCESSED_DIR
from src.ml import explain, segmentation as seg
from src.ml.predict import load_model
from src.ml.scoring import score_customers
from src.ml.segment_report import SEG_DIR, make_report
from src.ml.settings import DATA_PATH, MONITORED_GROUPS

from src.db.predictions import save_predictions



def main(save_to_db: bool = True, refit_cutoffs: bool = False) -> pd.DataFrame:
    cfg = seg.load_config()
    model, meta = load_model()
    version = meta["model_version"]

    df = pd.read_csv(DATA_PATH)
    cutoffs = seg.get_cutoffs(df["monthly_charges"], cfg, version, refit=refit_cutoffs)
    active = df[df["subscription_status"] == "active"].reset_index(drop=True)   # eligible customers

    scored = score_customers(active, cfg, cutoffs)
    out = pd.concat([active[["customer_id", "tenure", "internet_service", "monthly_charges"]], scored], axis=1)
    out = out.sort_values(["priority_rank", "expected_revenue_at_risk"], ascending=[True, False])

    # ---- files ----
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out.drop(
        columns=["top_risk_factors", "top_protective_factors"]
    ).to_csv(PROCESSED_DIR / f"customer_risk_{version}.csv", index=False)

    ref_prob = explain.reference_probability(model, explain.load_reference(version))
    make_report(out, active[MONITORED_GROUPS], cfg, meta, ref_prob)

    # ---- history ----
    if save_to_db:
        batch_id = "batch-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        n = save_predictions(out, batch_id)
        print(f"Stored {n:,} predictions in the database as {batch_id}")

    counts = out["risk_level"].value_counts().reindex(seg.ordered_names(cfg["risk_bands"]))
    print(f"Scored {len(out):,} active customers | flagged {int(out['flagged_for_review'].sum()):,} "
          f"| risk levels: {counts.to_dict()}")
    print(f"Report: reports/segmentation_report.md  |  charts: {SEG_DIR}")
    return out



if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-db", action="store_true", help="do everything except write to the database")
    ap.add_argument("--refit-cutoffs", action="store_true", help="recompute the value-tier cut-offs")
    args = ap.parse_args()
    main(save_to_db=not args.no_db, refit_cutoffs=args.refit_cutoffs)

