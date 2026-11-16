import json
import pandas as pd
from src.config import REPORTS_DIR



def build_summary(total_rows, missing_before, duplicate_rows, repaired, checks, valid, rejected, outliers) -> dict:
    reason_counts = checks.sum()
    reason_counts = reason_counts[reason_counts > 0].sort_values(ascending=False)
    
    return {
        "total_rows": int(total_rows),
        "valid_rows": int(len(valid)),
        "rejected_rows": int(len(rejected)),
        "rejection_rate_pct": round(100 * len(rejected) / total_rows, 2),
        "exact_duplicate_rows": int(duplicate_rows),
        "duplicate_customer_ids": int(checks["duplicate_customer_id"].sum()),
        "total_charges_repaired_for_new_customers": int(repaired),
        "missing_values_by_column": {k: int(v) for k, v in missing_before.items() if v > 0},
        "rejection_reasons": {k: int(v) for k, v in reason_counts.items()},
        "outliers_flagged": {k: int(v) for k, v in outliers.sum().items()},
    }


def write_reports(summary: dict, rejected: pd.DataFrame) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    (REPORTS_DIR / "data_quality_summary.json").write_text(json.dumps(summary, indent=2))
    
    rejected.to_csv(REPORTS_DIR / "rejected_records.csv", index=False)

    lines = [
        "# Data Quality Report", "",
        f"- Rows received: {summary['total_rows']}",
        f"- Valid rows: {summary['valid_rows']}",
        f"- Rejected rows: {summary['rejected_rows']} ({summary['rejection_rate_pct']}%)",
        f"- Exact duplicate rows: {summary['exact_duplicate_rows']}",
        f"- Duplicate customer IDs: {summary['duplicate_customer_ids']}",
        f"- Blank TotalCharges repaired to 0 (tenure = 0): "
        f"{summary['total_charges_repaired_for_new_customers']}"
    ]
    
    for title, key in [
        ("Missing values by column (before repair)", "missing_values_by_column"),
        ("Rejection reasons", "rejection_reasons"),
        ("Outliers flagged (kept in data)", "outliers_flagged")
    ]:
        lines += ["", f"## {title}"]
        lines += [f"- {k}: {v}" for k, v in summary[key].items()] or ["- none"]
        
    (REPORTS_DIR / "data_quality_report.md").write_text("\n".join(lines))

