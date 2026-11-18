import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from src.config import ADDON_COLS
from src.ml.settings import CATEGORICAL_FEATURES, ENGINEERED_NUMERIC, NUMERIC_FEATURES, RANDOM_STATE



def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create service-usage features from the raw columns. Runs inside the pipeline.
    """
    
    df = df.copy()
    df["num_addons"] = (df[ADDON_COLS] == "Yes").sum(axis=1)
    df["num_services"] = ((df["phone_service"] == "Yes").astype(int)
                          + (df["internet_service"] != "No").astype(int)
                          + df["num_addons"])
    df["charges_per_service"] = df["monthly_charges"] / df["num_services"].clip(lower=1)
    return df


def build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline([("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler())])
    
    categorical = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                            ("onehot", OneHotEncoder(handle_unknown="ignore"))])
    
    return ColumnTransformer(
        [
            ("num", numeric, NUMERIC_FEATURES + ENGINEERED_NUMERIC),
            ("cat", categorical, CATEGORICAL_FEATURES)
        ],
        sparse_threshold=0,        # always output a dense array (gradient boosting needs it)
    )


def candidate_models() -> dict:
    """The baseline comes first; the order matters in train.py."""
    
    return {
        "Logistic Regression (baseline)": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, 
            min_samples_leaf=10, 
            class_weight="balanced_subsample", 
            n_jobs=-1, 
            random_state=RANDOM_STATE
        ),
        "Gradient Boosting": HistGradientBoostingClassifier(
            learning_rate=0.05, 
            max_iter=200, 
            max_leaf_nodes=15, 
            min_samples_leaf=30,
            l2_regularization=1.0, 
            class_weight="balanced", 
            random_state=RANDOM_STATE
        ),
    }


def build_pipeline(classifier) -> Pipeline:
    return Pipeline([
        ("features", FunctionTransformer(add_engineered_features)),
        ("prep", build_preprocessor()),
        ("clf", classifier),
    ])