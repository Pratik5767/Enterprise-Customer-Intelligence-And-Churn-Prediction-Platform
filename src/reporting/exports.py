"""
Filtered customer-level CSV exports (reusable by the API and from the command line).
"""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config import ALLOWED_VALUES
from src.ml import segmentation as seg
from src.ml.segmentation import PREDICTION_NOTICE
from src.reporting.data import load_model_meta, load_portfolio
from src.reporting.metrics import split_portfolio
from src.reporting.settings import EXPORT_DIR
from src.db.session import SessionLocal



@dataclass
class ReportFilter:
    statuses:           list | None = None            # default: active customers only
    risk_levels:        list | None = None
    value_tiers:        list | None = None
    priority_ranks:     list | None = None
    contract_types:     list | None = None
    min_probability:    float | None = None
    max_probability:    float | None = None
    min_tenure:         int | None = None
    max_tenure:         int | None = None
    flagged_only:       bool = False
    scored_only:        bool = True

    def validate(self, risk_order: list, value_order: list) -> None:
        """
        Reject typos instead of silently returning an empty file.
        """
        
        def check(values, allowed, name):
            bad = sorted(set(values or []) - set(allowed))
            
            if bad:
                raise ValueError(f"Unknown {name} {bad}. Allowed: {sorted(allowed)}")
        
        check(self.statuses, {"active", "churned"}, "status")
        check(self.risk_levels, risk_order, "risk level")
        check(self.value_tiers, value_order, "value tier")
        check(self.contract_types, ALLOWED_VALUES["contract_type"], "contract type")
        
        if self.min_probability is not None and self.max_probability is not None \
                and self.min_probability > self.max_probability:
            raise ValueError("min_probability cannot be larger than max_probability")
        
        for p in (self.min_probability, self.max_probability):
            if p is not None and not 0 <= p <= 1:
                raise ValueError("Probabilities must be between 0 and 1")
        
        if self.min_tenure is not None and self.max_tenure is not None and self.min_tenure > self.max_tenure:
            raise ValueError("min_tenure cannot be larger than max_tenure")


def apply_filters(pf: pd.DataFrame, flt: ReportFilter) -> pd.DataFrame:
    d = pf[pf["subscription_status"].isin(flt.statuses or ["active"])]
    
    if flt.scored_only:
        d = d[d["has_score"]]
    
    for values, col in [(flt.risk_levels, "risk_level"), (flt.value_tiers, "value_tier"),
                        (flt.priority_ranks, "priority_rank"), (flt.contract_types, "contract_type")]:
        if values:
            d = d[d[col].isin(values)]
    
    if flt.min_probability is not None:
        d = d[d["probability"] >= flt.min_probability]
    if flt.max_probability is not None:
        d = d[d["probability"] <= flt.max_probability]
    if flt.min_tenure is not None:
        d = d[d["tenure"] >= flt.min_tenure]
    if flt.max_tenure is not None:
        d = d[d["tenure"] <= flt.max_tenure]
    if flt.flagged_only:
        d = d[d["flagged_for_review"]]
    
    return d.sort_values(["priority_rank", "expected_revenue_at_risk"], ascending=[True, False])


def export_frame(d: pd.DataFrame) -> pd.DataFrame:
    """
    The columns a business user needs. Sensitive attributes such as gender are never exported.
    """
    
    return pd.DataFrame({
        "customer_id": d["customer_id"], 
        "subscription_status": d["subscription_status"],
        "tenure_months": d["tenure"], 
        "contract_type": d["contract_type"],
        "internet_service": d["internet_service"], 
        "payment_method": d["payment_method"],
        "monthly_charges": d["monthly_charges"], 
        "churn_probability": d["probability"].round(4),
        "risk_level": d["risk_level"], 
        "value_tier": d["value_tier"],
        "priority_segment": d["priority_segment"], 
        "priority_rank": d["priority_rank"],
        "flagged_for_review": d["flagged_for_review"],
        "expected_annual_revenue_at_risk": d["expected_revenue_at_risk"].round(2),
        "model_version": d["model_version"], 
        "scored_on": d["prediction_date"].dt.strftime("%Y-%m-%d")
    })


def sanitize_for_csv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Stop spreadsheet programs from running text that starts like a formula (=, +, -, @).
    """
    
    def fix(v):
        return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r") else v
    
    out = df.copy()
    for c in out.select_dtypes(include=["object", "string", "category"]).columns:
        out[c] = out[c].astype(object).map(fix)
    return out


def write_export(d: pd.DataFrame, path, flt: ReportFilter) -> dict:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = sanitize_for_csv(export_frame(d))
    out.to_csv(path, index=False)
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), 
        "rows": len(out),
        "filters": asdict(flt), 
        "scores_from": [str(d["prediction_date"].min()), str(d["prediction_date"].max())],
        "note": PREDICTION_NOTICE
    }
    path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    return {"path": str(path), "rows": len(out)}


def main():
    ap = argparse.ArgumentParser(description="Export a filtered customer risk report to CSV.")
    ap.add_argument("--out", required=True, help="file name (saved in reports/exports/) or a full path")
    ap.add_argument("--status", nargs="*", dest="statuses")
    ap.add_argument("--risk", nargs="*", dest="risk_levels")
    ap.add_argument("--value-tier", nargs="*", dest="value_tiers")
    ap.add_argument("--priority-rank", nargs="*", type=int, dest="priority_ranks")
    ap.add_argument("--contract", nargs="*", dest="contract_types")
    ap.add_argument("--min-prob", type=float, dest="min_probability")
    ap.add_argument("--max-prob", type=float, dest="max_probability")
    ap.add_argument("--min-tenure", type=int)
    ap.add_argument("--max-tenure", type=int)
    ap.add_argument("--flagged-only", action="store_true")
    a = ap.parse_args()

    flt = ReportFilter(
        statuses=a.statuses, 
        risk_levels=a.risk_levels, 
        value_tiers=a.value_tiers,
        priority_ranks=a.priority_ranks, 
        contract_types=a.contract_types,
        min_probability=a.min_probability, 
        max_probability=a.max_probability,
        min_tenure=a.min_tenure, 
        max_tenure=a.max_tenure, 
        flagged_only=a.flagged_only
    )

    cfg = seg.load_config()
    
    try:
        flt.validate(seg.ordered_names(cfg["risk_bands"]), seg.ordered_names(cfg["value_tiers"]))
    except ValueError as e:
        raise SystemExit(f"Invalid filter: {e}")
    
    horizon = load_model_meta()["business_assumptions"]["horizon_months"]
    with SessionLocal() as db:
        pf, _, _ = split_portfolio(load_portfolio(db), horizon)
    
    d = apply_filters(pf, flt)
    if d.empty:
        raise SystemExit("No customers match this filter; nothing was written.")
    
    path = Path(a.out)
    if not path.is_absolute() and path.parent == Path("."):
        path = EXPORT_DIR / path
    
    info = write_export(d, path, flt)
    print(f"Wrote {info['rows']:,} rows to {info['path']}")




if __name__ == "__main__":
    main()