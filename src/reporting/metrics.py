import numpy as np
import pandas as pd

from src.reporting.settings import STALE_SCORES_DAYS



def split_portfolio(pf: pd.DataFrame, horizon: int):
    """
    Add revenue columns; return (all customers, active customers, active customers WITH a current score).
    """
    
    pf = pf.copy()
    pf["annual_value"] = pf["monthly_charges"] * horizon
    pf["expected_revenue_at_risk"] = pf["probability"] * pf["annual_value"]
    active = pf[pf["churn_flag"] == 0]
    scored = active[active["has_score"]].copy()
    if not scored.empty:
        scored["priority_rank"] = scored["priority_rank"].astype(int)
    return pf, active, scored


def headline_kpis(pf, active, scored, risk_order, horizon) -> dict:
    total = len(pf)
    churned = int(pf["churn_flag"].sum())
    mrr_total = float(pf["monthly_charges"].sum())
    mrr_churned = float(pf.loc[pf["churn_flag"] == 1, "monthly_charges"].sum())
    high = risk_order[-1]
    in_high = scored[scored["risk_level"] == high]
    n_scored = len(scored)
    
    return {
        "total_customers": total,
        "churned_customers": churned,
        "retained_customers": total - churned,
        "churn_rate_pct": round(100 * churned / total, 1) if total else 0.0,
        "total_monthly_billing": round(mrr_total, 2),
        "churned_monthly_billing": round(mrr_churned, 2),
        "churned_billing_share_pct": round(100 * mrr_churned / mrr_total, 1) if mrr_total else 0.0,
        "active_customers": len(active),
        "active_scored": n_scored,
        "active_unscored": len(active) - n_scored,
        "flagged_for_review": int(scored["flagged_for_review"].sum()),
        "high_band_name": high,
        "high_band_customers": len(in_high),
        "high_band_pct": round(100 * len(in_high) / n_scored, 1) if n_scored else 0.0,
        "high_band_monthly_billing": round(float(in_high["monthly_charges"].sum()), 2),
        "avg_probability": round(float(scored["probability"].mean()), 4) if n_scored else None,
        "active_annual_billing": round(float(scored["annual_value"].sum()), 2),
        "expected_revenue_at_risk": round(float(scored["expected_revenue_at_risk"].sum()), 2),
        "horizon_months": horizon,
    }


def risk_by_segment(scored: pd.DataFrame, col: str, risk_order: list) -> pd.DataFrame:
    """
    For each segment: size, average risk, risk-band mix, billing and expected revenue at risk.
    """
    
    high = risk_order[-1]
    d = scored.assign(is_high=(scored["risk_level"] == high).astype(int))
    base = d.groupby(col, observed=True).agg(
        customers=("customer_id", "size"),
        avg_probability=("probability", "mean"),
        pct_high_risk=("is_high", "mean"),
        pct_flagged=("flagged_for_review", "mean"),
        monthly_billing=("monthly_charges", "sum"),
        expected_revenue_at_risk=("expected_revenue_at_risk", "sum")
    )
    
    mix = (pd.crosstab(d[col], d["risk_level"], normalize="index")
             .reindex(columns=risk_order, fill_value=0) * 100)
    
    mix.columns = [f"pct_{c}" for c in mix.columns]
    base.index, mix.index = base.index.astype(str), mix.index.astype(str)
    out = base.join(mix).rename_axis(col).reset_index()
    total_loss = out["expected_revenue_at_risk"].sum()
    out["share_of_expected_loss_pct"] = 100 * out["expected_revenue_at_risk"] / total_loss if total_loss else 0.0
    out["pct_high_risk"] = 100 * out["pct_high_risk"]
    out["pct_flagged"] = 100 * out["pct_flagged"]
    pct_cols = [c for c in out.columns if c.startswith("pct_") or c == "share_of_expected_loss_pct"]
    out[pct_cols] = out[pct_cols].round(1)
    out["avg_probability"] = out["avg_probability"].round(3)
    out["monthly_billing"] = out["monthly_billing"].round(0)
    out["expected_revenue_at_risk"] = out["expected_revenue_at_risk"].round(0)
    return out


def revenue_by_band(scored: pd.DataFrame, risk_order: list) -> pd.DataFrame:
    g = (scored.groupby("risk_level")
               .agg(customers=("customer_id", "size"), monthly_billing=("monthly_charges", "sum"),
                    expected_revenue_at_risk=("expected_revenue_at_risk", "sum"))
               .reindex(risk_order).fillna(0).rename_axis("risk_level").reset_index())
    g["customers"] = g["customers"].astype(int)
    g["customers_pct"] = 100 * g["customers"] / max(g["customers"].sum(), 1)
    total = g["expected_revenue_at_risk"].sum()
    g["expected_pct"] = 100 * g["expected_revenue_at_risk"] / total if total else 0.0
    
    return g.round({
        "monthly_billing": 0, 
        "expected_revenue_at_risk": 0, 
        "customers_pct": 1, 
        "expected_pct": 1
    })


def priority_table(scored: pd.DataFrame) -> pd.DataFrame:
    g = (scored.groupby(["priority_rank", "priority_segment"])
               .agg(customers=("customer_id", "size"), avg_probability=("probability", "mean"),
                    monthly_billing=("monthly_charges", "sum"),
                    expected_revenue_at_risk=("expected_revenue_at_risk", "sum"))
               .reset_index()
               .sort_values(["priority_rank", "expected_revenue_at_risk"], ascending=[True, False]))
    
    return g.round({
        "avg_probability": 3, 
        "monthly_billing": 0, 
        "expected_revenue_at_risk": 0
    }).reset_index(drop=True)


def concentration_curve(scored: pd.DataFrame) -> pd.DataFrame:
    """
    Customers ranked by expected loss (highest first): what share of the total do the top x% hold?
    """
    
    loss = np.sort(scored["expected_revenue_at_risk"].to_numpy(dtype=float))[::-1]
    n = len(loss)
    if n == 0:
        return pd.DataFrame({"customer_share": [], "loss_share": []})
    x = np.arange(1, n + 1) / n
    total = loss.sum()
    return pd.DataFrame({"customer_share": x, "loss_share": np.cumsum(loss) / total if total > 0 else x})


def top_share(curve: pd.DataFrame, share: float):
    if curve.empty:
        return None
    i = int(np.searchsorted(curve["customer_share"].to_numpy(), share - 1e-9, side="left"))
    return float(curve["loss_share"].iloc[min(i, len(curve) - 1)])


def risk_trend(hist: pd.DataFrame, high_cutoff: float, horizon: int) -> pd.DataFrame:
    """
    One row per scoring run. Uses the stored PROBABILITY (labels can change if the config changes).
    """
    
    if hist.empty:
        return pd.DataFrame()
    h = hist.assign(expected=hist["probability"] * hist["monthly_charges"] * horizon,
                    high=(hist["probability"] >= high_cutoff).astype(int))
    t = (h.groupby("batch_id")
           .agg(scored_on=("prediction_date", "max"), customers=("probability", "size"),
                avg_probability=("probability", "mean"), pct_high=("high", "mean"),
                expected_revenue_at_risk=("expected", "sum"), model_version=("model_version", "first"))
           .reset_index().sort_values("scored_on").reset_index(drop=True))
    t["pct_high"] = (100 * t["pct_high"]).round(1)
    t["avg_probability"] = t["avg_probability"].round(4)
    t["expected_revenue_at_risk"] = t["expected_revenue_at_risk"].round(0)
    return t


def risk_movers(hist: pd.DataFrame, min_change: float = 0.10, top: int = 10):
    """
    Compare the last two scoring runs customer by customer. None if there are fewer than two runs.
    """
    
    if hist.empty or hist["batch_id"].nunique() < 2:
        return None
    order = hist.groupby("batch_id")["prediction_date"].max().sort_values()
    prev_id, last_id = order.index[-2], order.index[-1]
    a = hist[hist["batch_id"] == prev_id].set_index("customer_id")["probability"].rename("previous")
    b = hist[hist["batch_id"] == last_id].set_index("customer_id")["probability"].rename("latest")
    both = pd.concat([a, b], axis=1, join="inner")
    both["change"] = both["latest"] - both["previous"]
    
    return {
        "previous_batch": prev_id, 
        "latest_batch": last_id, 
        "customers_compared": len(both),
        "min_change": min_change,
        "rose": int((both["change"] >= min_change).sum()),
        "fell": int((both["change"] <= -min_change).sum()),
        "top_increases": both.sort_values("change", ascending=False).head(top).round(3).reset_index()
    }


def data_notes(active, scored, risk_order, include_synthetic=False) -> list:
    """
    Plain-language warnings about the data behind the report.
    """
    
    notes = []
    
    if len(active) > len(scored):
        notes.append(f"{len(active) - len(scored):,} active customers have no stored score and are left out of "
                     "the risk sections. Run: python -m src.ml.segment_run")
    if not scored.empty:
        newest, oldest = scored["prediction_date"].max(), scored["prediction_date"].min()
        age = (pd.Timestamp.now(tz="UTC") - newest).days
        if age > STALE_SCORES_DAYS:
            notes.append(f"The newest scores are {age} days old. Re-score before using these numbers to act.")
        if scored["batch_id"].nunique() > 1:
            notes.append(f"Current scores come from {scored['batch_id'].nunique()} different scoring runs "
                         f"(oldest {oldest:%Y-%m-%d}). Re-run the scoring so every customer has a fresh score.")
        unknown = sorted(set(scored["risk_level"].dropna()) - set(risk_order))
        if unknown:
            notes.append(f"Some stored risk labels {unknown} are not in config/segmentation.json, so band "
                         "comparisons may be incomplete.")
    if include_synthetic:
        notes.append("SYNTHETIC DEMO HISTORY is included in the trend section. Those scoring runs are fake and "
                     "exist only to test the charts.")
    
    return notes

