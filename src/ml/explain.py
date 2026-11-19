"""
Per-customer explanations: which factors push THIS customer's risk above or below a typical customer's.
"""

import json

import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR
from src.ml.settings import CATEGORICAL_FEATURES, DATA_PATH, INPUT_FEATURES, MODEL_VERSION, MODELS_DIR, NUMERIC_FEATURES



# factor name -> (input columns replaced TOGETHER, how to display this customer's value)
# Related columns are grouped so the what-if never builds an impossible customer
# (e.g. tenure changed but total_charges left behind).
_OTHER_ADDONS = ["online_backup", "device_protection", "streaming_tv", "streaming_movies"]

FACTOR_GROUPS = {
    "Contract type": (["contract_type"], lambda r: r["contract_type"]),
    "Tenure": (["tenure", "total_charges"], lambda r: f"{int(r['tenure'])} months"),
    "Monthly charges": (["monthly_charges"], lambda r: f"{r['monthly_charges']:.2f}"),
    "Internet service": (["internet_service"], lambda r: r["internet_service"]),
    "Tech support / online security": (
        ["tech_support", "online_security"],
        lambda r: f"tech support: {r['tech_support']}, online security: {r['online_security']}"),
    "Other add-on services": (
        _OTHER_ADDONS, lambda r: f"{sum(r[c] == 'Yes' for c in _OTHER_ADDONS)} of 4 active"),
    "Phone service": (
        ["phone_service", "multiple_lines"],
        lambda r: f"phone: {r['phone_service']}, multiple lines: {r['multiple_lines']}"),
    "Payment method": (["payment_method"], lambda r: r["payment_method"]),
    "Paperless billing": (["paperless_billing"], lambda r: r["paperless_billing"]),
    "Household": (["partner", "dependents"],
                  lambda r: f"partner: {r['partner']}, dependents: {r['dependents']}"),
    "Senior citizen": (["senior_citizen"], lambda r: r["senior_citizen"]),
}

# Factors the model uses but that we do NOT show on customer-facing cards. Showing an age-related
# attribute as a "reason" can invite unequal treatment. This is a policy choice: change it deliberately.
HIDE_FROM_DISPLAY = {"Senior citizen"}

_covered = [c for cols, _ in FACTOR_GROUPS.values() for c in cols]
assert sorted(_covered) == sorted(INPUT_FEATURES), "Every model input must belong to exactly one factor group"


def build_reference(path=DATA_PATH, split_path=PROCESSED_DIR / "train_test_split.csv") -> dict:
    """
    A 'typical customer': median of numeric inputs, most common value of categorical ones (training data).
    """
    
    df = pd.read_csv(path)
    if split_path.exists():
        split = pd.read_csv(split_path)
        df = df[df["customer_id"].isin(split.loc[split["split"] == "train", "customer_id"])]
    ref = {c: float(df[c].median()) for c in NUMERIC_FEATURES}
    ref.update({c: str(df[c].mode().iloc[0]) for c in CATEGORICAL_FEATURES})
    return ref


def load_reference(version: str = MODEL_VERSION) -> dict:
    """
    Saved next to the model. Bump MODEL_VERSION when you retrain so a fresh reference is built.
    """
    
    path = MODELS_DIR / f"reference_profile_{version}.json"
    if path.exists():
        return json.loads(path.read_text())
    ref = build_reference()
    MODELS_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(ref, indent=2))
    return ref


def reference_probability(model, reference: dict) -> float:
    return float(model.predict_proba(pd.DataFrame([reference])[INPUT_FEATURES])[0, 1])


def explain_batch(model, X: pd.DataFrame, reference: dict, top_k: int = 3, min_effect: float = 0.01) -> pd.DataFrame:
    """
    For each customer: how many probability points each factor adds or removes vs the typical profile.
    """
    
    X = X.reset_index(drop=True)
    base = model.predict_proba(X)[:, 1]
    names = list(FACTOR_GROUPS)
    effects = np.zeros((len(X), len(names)))
    
    for j, name in enumerate(names):
        X_typical = X.copy()
        for col in FACTOR_GROUPS[name][0]:
            X_typical[col] = reference[col]                     # swap this factor for the typical value
        effects[:, j] = base - model.predict_proba(X_typical)[:, 1]

    visible = [j for j, n in enumerate(names) if n not in HIDE_FROM_DISPLAY]
    rows = []

    for i in range(len(X)):
        customer = X.iloc[i]
        order = sorted(visible, key=lambda j: effects[i, j])
        raising = [j for j in order[::-1][:top_k] if effects[i, j] >= min_effect]
        lowering = [j for j in order[:top_k] if effects[i, j] <= -min_effect]
        pack = lambda js: [{
            "factor": names[j],
            "value": FACTOR_GROUPS[names[j]][1](customer),
            "effect_pct_points": round(float(effects[i, j]) * 100, 1)
        } for j in js]

        rows.append({
            "top_risk_factors": pack(raising), 
            "top_protective_factors": pack(lowering)
        })
    
    return pd.DataFrame(rows)


def factors_text(factors: list) -> str:
    if not factors:
        return "none stands out"
    return "; ".join(f"{f['factor']} ({f['value']}) {f['effect_pct_points']:+.1f} pts" for f in factors)

