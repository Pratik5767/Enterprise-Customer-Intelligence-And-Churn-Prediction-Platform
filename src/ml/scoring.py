import pandas as pd

from src.ml import explain, segmentation as seg
from src.ml.predict import load_model, predict_batch
from src.ml.settings import INPUT_FEATURES



def score_customers(raw: pd.DataFrame, cfg: dict, cutoffs: dict, top_k: int = 3) -> pd.DataFrame:
    """
    Probability + risk level + value tier + priority + explanation for each customer record.

    Used by the batch run now and by the FastAPI prediction endpoint on Day 4.
    """
    
    raw = raw.reset_index(drop=True)
    model, meta = load_model()
    horizon = meta["business_assumptions"]["horizon_months"]

    scores = predict_batch(raw).rename(columns={"predicted_churn": "flagged_for_review"})
    segs = seg.build_segments(raw, scores["churn_probability"], cfg, cutoffs, horizon)
    expl = explain.explain_batch(
        model, 
        raw[INPUT_FEATURES],
        explain.load_reference(meta["model_version"]), 
        top_k=top_k
    )

    out = pd.concat([scores, segs, expl], axis=1)
    out["plain_language_risk"] = out["churn_probability"].map(seg.plain_language)
    out["review_action"] = out["priority_rank"].map(seg.RANK_ACTIONS)
    out["top_risk_factors_text"] = out["top_risk_factors"].map(explain.factors_text)
    out["top_protective_factors_text"] = out["top_protective_factors"].map(explain.factors_text)
    
    return out


