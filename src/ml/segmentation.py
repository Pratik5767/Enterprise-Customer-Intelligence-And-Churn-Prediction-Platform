"""
Risk bands, value tiers, lifecycle segments and the priority matrix (all configurable).
"""

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.config import BASE_DIR
from src.ml.pipeline import add_engineered_features
from src.ml.settings import MODELS_DIR



CONFIG_PATH = BASE_DIR / "config" / "segmentation.json"

PREDICTION_NOTICE = (
    "A risk score is an estimate of likelihood, not a confirmed decision by the customer to leave. "
    "Scores are for human review and prioritisation only; they must not trigger automatic account actions."
)

DEFAULT_CONFIG = {
    # Each group maps  name -> LOWER bound. A group runs up to the next group's lower bound.
    "risk_bands": {"Low": 0.0, "Medium": 0.30, "High": 0.60},                   # churn probability
    "value_tiers": {"Low value": 0.0, "Mid value": 0.50, "High value": 0.75},   # quantile of monthly charges
    "tenure_segments": {
        "New (0-12 months)": 0, 
        "Developing (13-24 months)": 13,
        "Established (25-48 months)": 25, 
        "Loyal (49+ months)": 49
    },
    "usage_bands": {
        "Light (1-2 services)": 0, 
        "Moderate (3-4 services)": 3,
        "Heavy (5+ services)": 5
    },                              # number of services held
    # "<risk band>|<value tier>" -> segment label and review rank (1 = look first)
    "priority_matrix": {
        "High|High value":   {"label": "Critical: high value, high risk",   "rank": 1},
        "High|Mid value":    {"label": "Priority: mid value, high risk",    "rank": 2},
        "Medium|High value": {"label": "Priority: high value, medium risk", "rank": 2},
        "High|Low value":    {"label": "Standard: low value, high risk",    "rank": 3},
        "Medium|Mid value":  {"label": "Standard: mid value, medium risk",  "rank": 3},
        "Medium|Low value":  {"label": "Monitor: low value, medium risk",   "rank": 4},
        "Low|High value":    {"label": "Protect: high value, low risk",     "rank": 4},
        "Low|Mid value":     {"label": "Healthy: mid value, low risk",      "rank": 4},
        "Low|Low value":     {"label": "Healthy: low value, low risk",      "rank": 4},
    },
}

RANK_ACTIONS = {
    1: "Review first: consider personal outreach from a customer-success rep",
    2: "Review this cycle: consider a proactive check-in or retention offer",
    3: "Review if capacity allows: consider low-cost outreach",
    4: "No action needed now: keep monitoring",
}


def validate_config(cfg: dict) -> None:
    for key in ("risk_bands", "value_tiers", "tenure_segments", "usage_bands"):
        bounds = list(cfg[key].values())
        if len(set(bounds)) != len(bounds):
            raise ValueError(f"{key}: every group needs a different lower bound")
    
    missing = [
        f"{r}|{v}" 
        for r in cfg["risk_bands"] for v in cfg["value_tiers"]
        if f"{r}|{v}" not in cfg["priority_matrix"]
    ]

    if missing:
        raise ValueError(f"priority_matrix is missing combinations: {missing}")


def load_config(path=CONFIG_PATH) -> dict:
    """
    Read the config. On the first run the defaults are written to disk so you can edit them.
    """
    
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
    cfg = json.loads(path.read_text())
    validate_config(cfg)
    return cfg


def ordered_names(bands: dict) -> list:
    return [name for name, _ in sorted(bands.items(), key=lambda kv: kv[1])]


def assign_bands(values: pd.Series, bands: dict) -> pd.Series:
    """
    Put each value into the group whose lower bound it has reached.
    """
    
    items = sorted(bands.items(), key=lambda kv: kv[1])
    names = [name for name, _ in items]
    edges = [-np.inf] + [bound for _, bound in items[1:]] + [np.inf]
    return pd.cut(values, bins=edges, labels=names, right=False)        # [low, high): low is included


# value tiers
def get_cutoffs(monthly_charges: pd.Series, cfg: dict, version: str, refit: bool = False) -> dict:
    """
    Turn the value-tier quantiles into money cut-offs, and save them so every run (and the API) agrees.
    """
    
    path = MODELS_DIR / f"segmentation_cutoffs_{version}.json"
    tiers = sorted(cfg["value_tiers"].items(), key=lambda kv: kv[1])
    wanted = dict(tiers)
    
    if path.exists() and not refit:
        saved = json.loads(path.read_text())
        if saved.get("quantiles") == wanted:
            return saved
        print("Value-tier settings changed in the config: refitting cut-offs.")
    
    cutoffs = {
        "value_tiers": {
            name: (0.0 if i == 0 else round(float(monthly_charges.quantile(q)), 2))
            for i, (name, q) in enumerate(tiers)
        },
        "quantiles": wanted,
        "fitted_at": datetime.now(timezone.utc).isoformat(),
        "n_customers": int(len(monthly_charges)),
    }
    MODELS_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(cutoffs, indent=2))
    return cutoffs


def load_cutoffs(version: str) -> dict:
    path = MODELS_DIR / f"segmentation_cutoffs_{version}.json"
    if not path.exists():
        raise FileNotFoundError("Run `python -m src.ml.segment_run` once to fit the value-tier cut-offs.")
    return json.loads(path.read_text())


# segments
def build_segments(raw: pd.DataFrame, proba, cfg: dict, cutoffs: dict, horizon_months: int) -> pd.DataFrame:
    """
    Risk level, value tier, priority, lifecycle segments and revenue at risk for each customer.
    """
    
    raw = add_engineered_features(raw.reset_index(drop=True))
    p = pd.Series(np.asarray(proba, dtype=float), name="churn_probability")
    out = pd.DataFrame(index=raw.index)
    
    out["risk_level"] = assign_bands(p, cfg["risk_bands"])
    out["value_tier"] = assign_bands(raw["monthly_charges"], cutoffs["value_tiers"])
    key = out["risk_level"].astype(str) + "|" + out["value_tier"].astype(str)
    out["priority_segment"] = key.map(lambda k: cfg["priority_matrix"][k]["label"])
    out["priority_rank"] = key.map(lambda k: cfg["priority_matrix"][k]["rank"]).astype(int)
    out["tenure_segment"] = assign_bands(raw["tenure"], cfg["tenure_segments"])
    out["subscription_type"] = raw["contract_type"]
    out["usage_band"] = assign_bands(raw["num_services"], cfg["usage_bands"])
    out["num_services"] = raw["num_services"]
    out["annual_value"] = (raw["monthly_charges"] * horizon_months).round(2)
    out["expected_revenue_at_risk"] = (p * out["annual_value"]).round(2)
    
    return out


def plain_language(p: float) -> str:
    return (
        f"Among customers with similar scores in the historical data, about {p * 100:.0f} in 100 left. "
            "This is a likelihood, not a decision."
    )

