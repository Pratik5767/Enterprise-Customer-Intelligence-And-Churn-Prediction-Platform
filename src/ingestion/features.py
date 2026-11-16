import numpy as np
import pandas as pd
from src.config import CATEGORICAL_COLS


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    df["senior_citizen"] = df["senior_citizen"].map({"0": "No", "1": "Yes"})   # same style as other Yes/No columns
    
    for col in CATEGORICAL_COLS:
        df[col] = df[col].astype("category")
    
    df["tenure"] = df["tenure"].astype(int)
    df["subscription_status"] = np.where(df["churn"] == "Yes", "churned", "active")
    
    return df