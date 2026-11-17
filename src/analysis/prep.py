import pandas as pd
from src.config import ADDON_COLS, PROCESSED_DIR



TENURE_BINS = [-1, 12, 24, 48, 72, 120]
TENURE_LABELS = ["0-12", "13-24", "25-48", "49-72", "73+"]
CHARGE_LABELS = ["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"]


def load_clean(path=PROCESSED_DIR / "customers_clean.csv") -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["subscription_start"])

    # Numeric versions of Yes/No columns (needed for averages and correlations)
    df["churn_flag"] = (df["churn"] == "Yes").astype(int)
    df["senior_flag"] = (df["senior_citizen"] == "Yes").astype(int)

    # Buckets: turn continuous numbers into comparable groups
    df["tenure_bucket"] = pd.cut(df["tenure"], bins=TENURE_BINS, labels=TENURE_LABELS)
    df["monthly_charge_band"] = pd.qcut(df["monthly_charges"], 4, labels=CHARGE_LABELS)

    # Service usage: how many services does each customer actually have?
    df["num_addons"] = (df[ADDON_COLS] == "Yes").sum(axis=1)
    df["num_services"] = (
        (df["phone_service"] == "Yes").astype(int)
        + (df["internet_service"] != "No").astype(int)
        + df["num_addons"]
    )
    
    return df

