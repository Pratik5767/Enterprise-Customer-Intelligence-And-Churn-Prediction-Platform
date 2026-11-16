import pandas as pd
from src.config import ADDON_COLS, ALLOWED_VALUES, CUSTOMER_ID_PATTERN, MAX_TENURE, NUMERIC_COLS, SNAPSHOT_DATE



def run_checks(df: pd.DataFrame, type_errors: pd.DataFrame) -> pd.DataFrame:
    """
    Return a table: one row per customer, one True/False column per rule (True = violation).
    """

    c = {}
    cid = df["customer_id"]

    # --- customer ID ---
    c["missing_customer_id"] = cid.isna()
    c["bad_customer_id_format"] = cid.notna() & ~cid.fillna("").str.match(CUSTOMER_ID_PATTERN)
    c["duplicate_customer_id"] = cid.notna() & cid.duplicated(keep="first")

    # --- numeric columns: wrong type / missing ---
    for col in NUMERIC_COLS:
        c[f"invalid_type_{col}"] = type_errors[col]
        c[f"missing_{col}"] = df[col].isna() & ~type_errors[col]

    # --- numeric columns: impossible values ---
    c["invalid_tenure"] = df["tenure"].notna() & ((df["tenure"] < 0) | (df["tenure"] > MAX_TENURE))
    c["invalid_monthly_charges"] = df["monthly_charges"].notna() & (df["monthly_charges"] <= 0)
    c["invalid_total_charges"] = df["total_charges"].notna() & (df["total_charges"] < 0)

    # --- subscription date ---
    c["subscription_start_in_future"] = (
        df["subscription_start"].notna() & (df["subscription_start"] > pd.Timestamp(SNAPSHOT_DATE))
    )

    # --- categorical columns: missing / value not allowed ---
    for col, allowed in ALLOWED_VALUES.items():
        c[f"missing_{col}"] = df[col].isna()
        c[f"invalid_{col}"] = df[col].notna() & ~df[col].isin(allowed)

    # --- service-usage consistency ---
    no_internet = df["internet_service"] == "No"
    for col in ADDON_COLS:
        c[f"inconsistent_{col}"] = no_internet & df[col].notna() & (df[col] != "No internet service")
    
    c["inconsistent_multiple_lines"] = (
        (df["phone_service"] == "No") & df["multiple_lines"].notna() & (df["multiple_lines"] != "No phone service")
    )

    return pd.DataFrame(c)


def split_valid_rejected(df: pd.DataFrame, checks: pd.DataFrame, original: pd.DataFrame):
    """Rows failing ANY rule go to 'rejected', along with a readable list of reasons."""
    
    failed = checks.any(axis=1)
    reasons = checks.apply(lambda row: ";".join(row.index[row.to_numpy()]), axis=1)
    valid = df[~failed].copy()
    rejected = original[failed].copy()                  # original text values, so you can see what was wrong
    rejected["rejection_reasons"] = reasons[failed]
    
    return valid, rejected

