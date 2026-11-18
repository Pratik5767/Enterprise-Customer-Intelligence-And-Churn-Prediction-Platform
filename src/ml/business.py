import numpy as np
import pandas as pd

from src.ml.settings import CAPACITY_SHARE, CONTACT_COST, SUCCESS_RATE



def business_outcome(y_true, proba, value, threshold, contact_cost=CONTACT_COST, success_rate=SUCCESS_RATE) -> dict:
    """
    What happens if we contact every customer whose probability >= threshold?

    value = money at stake per customer (monthly charges x horizon).
    """
    
    y_true, proba, value = map(np.asarray, (y_true, proba, value))
    contacted = proba >= threshold
    tp = contacted & (y_true == 1)          # contacted, and would really have left
    fp = contacted & (y_true == 0)          # contacted, but would have stayed anyway
    fn = ~contacted & (y_true == 1)         # not contacted, and left
    n_contacted = int(contacted.sum())

    saved = float(success_rate * value[tp].sum())       # expected revenue retained
    cost = float(contact_cost * n_contacted)
    
    return {
        "contacted": n_contacted,
        "contacted_share": n_contacted / len(y_true),
        "true_positives": int(tp.sum()),
        "false_positives": int(fp.sum()),
        "false_negatives": int(fn.sum()),
        "precision": float(tp.sum() / n_contacted) if n_contacted else 0.0,
        "recall": float(tp.sum() / (y_true == 1).sum()),
        "revenue_saved": saved,
        "campaign_cost": cost,
        "net_benefit": saved - cost,
        "missed_churn_value": float(value[fn].sum()),
        "wasted_contact_cost": float(contact_cost * fp.sum()),
    }


def threshold_table(y_true, proba, value, thresholds=None, **assumptions) -> pd.DataFrame:
    """Try many thresholds and record the business outcome of each."""
    
    if thresholds is None:
        thresholds = np.round(np.arange(0.05, 0.96, 0.01), 2)
    
    return pd.DataFrame([
        {
            "threshold": float(t),
            **business_outcome(y_true, proba, value, t, **assumptions)
        } for t in thresholds
    ])


def choose_threshold(table: pd.DataFrame, capacity_share: float = CAPACITY_SHARE) -> float:
    """Best net benefit among thresholds that don't exceed the team's capacity."""
    
    feasible = table[table["contacted_share"] <= capacity_share]
    
    if feasible.empty:                                   # capacity smaller than even the top threshold
        return float(table["threshold"].max())
    
    return float(feasible.loc[feasible["net_benefit"].idxmax(), "threshold"])

