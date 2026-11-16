import pandas as pd



def iqr_bounds(series: pd.Series, k: float = 1.5):
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def flag_outliers(df: pd.DataFrame, cols=("monthly_charges", "total_charges")) -> pd.DataFrame:
    """Return True/False flags. Outliers are FLAGGED, not removed."""
    
    flags = pd.DataFrame(index=df.index)
    for col in cols:
        low, high = iqr_bounds(df[col].dropna())
        flags[f"{col}_outlier"] = (df[col] < low) | (df[col] > high)
    return flags