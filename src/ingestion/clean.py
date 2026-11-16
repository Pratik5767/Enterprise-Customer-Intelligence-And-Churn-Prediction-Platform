import numpy as np
import pandas as pd
from src.config import COLUMN_MAP, NUMERIC_COLS, SNAPSHOT_DATE



def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=COLUMN_MAP)
    missing = set(COLUMN_MAP.values()) - set(df.columns)
    
    if missing:
        raise ValueError(f"Dataset is missing expected columns: {sorted(missing)}")
    
    return df[list(COLUMN_MAP.values())]      # keep only the expected columns, in order


def clean_text(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace; treat empty strings as missing."""
    
    df = df.apply(lambda s: s.map(lambda v: v.strip() if isinstance(v, str) else v))
    return df.replace("", np.nan)


def convert_types(df: pd.DataFrame):
    """Convert numeric columns. Also record WHICH values failed to convert."""
    
    df = df.copy()
    type_errors = pd.DataFrame(index=df.index)
    
    for col in NUMERIC_COLS:
        converted = pd.to_numeric(df[col], errors="coerce")       # bad text -> NaN
        type_errors[col] = df[col].notna() & converted.isna()     # had a value, but it wasn't a number
        df[col] = converted
    
    return df, type_errors


def repair_total_charges(df: pd.DataFrame):
    """Known quirk: brand-new customers (tenure 0) have a blank TotalCharges. Their true total is 0."""
    
    df = df.copy()
    mask = (df["tenure"] == 0) & df["total_charges"].isna()
    df.loc[mask, "total_charges"] = 0.0
    return df, int(mask.sum())


def add_subscription_start(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    snapshot = pd.Timestamp(SNAPSHOT_DATE)
    df["subscription_start"] = snapshot - pd.to_timedelta(df["tenure"] * 30, unit="D")
    return df

