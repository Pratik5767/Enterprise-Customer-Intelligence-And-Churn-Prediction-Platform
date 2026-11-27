from src.config import REPORTS_DIR



EXEC_DIR = REPORTS_DIR / "executive"
EXPORT_DIR = REPORTS_DIR / "exports"
CUSTOMER_DIR = REPORTS_DIR / "customers"

CURRENCY = "$"                    # the Telco sample is in dollars; change if your data is not
SYNTHETIC_PREFIX = "synthetic-"   # batch ids starting like this are FAKE demo history
MIN_SEGMENT_SIZE = 30             # smaller segments are ignored when ranking
STALE_SCORES_DAYS = 30
TOP_CUSTOMER_REPORTS = 10         # individual reports written for the highest-exposure customers

SEGMENT_DIMENSIONS = {
    "contract_type": "Contract type",
    "tenure_bucket": "Tenure (months)",
    "value_tier": "Value tier",
    "internet_service": "Internet service",
    "payment_method": "Payment method",
}
