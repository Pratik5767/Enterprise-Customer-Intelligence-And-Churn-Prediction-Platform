import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency



def wilson_ci(k, n, z=1.96):
    """
    95% confidence interval for a proportion (Wilson method). Works well for small groups.
    """
    
    k = np.asarray(k, float)
    n = np.asarray(n, float)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    
    return centre - half, centre + half


def churn_by(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Churn rate for each value of `col`, with group size and a 95% confidence interval.
    """
    
    g = (
        df.groupby(col, observed=True)["churn_flag"].agg(customers="size", churned="sum").reset_index()
    )
    lo, hi = wilson_ci(g["churned"], g["customers"])
    g["churn_rate_pct"] = (100 * g["churned"] / g["customers"]).round(1)
    g["ci_low_pct"] = (100 * lo).round(1)
    g["ci_high_pct"] = (100 * hi).round(1)
    
    return g


def association_with_churn(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    How strongly is each categorical feature associated with churn? (Cramér's V, 0 to 1)
    """
    
    rows = []

    for col in cols:
        table = pd.crosstab(df[col], df["churn_flag"])
        chi2, p, _, _ = chi2_contingency(table, correction=False)
        k = min(table.shape) - 1
        v = np.sqrt(chi2 / (table.to_numpy().sum() * k))
        rows.append({"feature": col, "cramers_v": round(float(v), 3), "p_value": float(p)})
    
    out = pd.DataFrame(rows).sort_values("cramers_v", ascending=False).reset_index(drop=True)
    out["strength"] = pd.cut(out["cramers_v"], [-0.01, 0.1, 0.3, 1.01], labels=["weak", "moderate", "strong"])
    return out


def numeric_summary(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Mean and median of numeric features for churned vs retained customers.
    """
    
    rows = []
    
    for c in cols:
        a = df.loc[df["churn_flag"] == 1, c]
        b = df.loc[df["churn_flag"] == 0, c]
        rows.append({
            "feature": c,
            "churned_mean": round(a.mean(), 1), 
            "retained_mean": round(b.mean(), 1),
            "churned_median": round(a.median(), 1), 
            "retained_median": round(b.median(), 1)
        })
    
    return pd.DataFrame(rows)


def revenue_summary(df: pd.DataFrame) -> dict:
    total = df["monthly_charges"].sum()
    churned_rev = df.loc[df["churn_flag"] == 1, "monthly_charges"].sum()
    
    return {
        "total_monthly_charges": round(float(total), 2),
        "monthly_charges_of_churned_customers": round(float(churned_rev), 2),
        "share_of_monthly_charges_pct": round(100 * float(churned_rev) / float(total), 1),
    }


def contrast_sentence(table: pd.DataFrame, col: str) -> str:
    """
    Describe the spread of churn across groups, using non-causal wording.
    """
    
    hi = table.loc[table["churn_rate_pct"].idxmax()]
    lo = table.loc[table["churn_rate_pct"].idxmin()]
    
    return (
        f"Within **{col}**, observed churn ranges from {lo['churn_rate_pct']}% "
        f"({lo[col]}, n={int(lo['customers']):,}) to {hi['churn_rate_pct']}% "
        f"({hi[col]}, n={int(hi['customers']):,})."
    )

