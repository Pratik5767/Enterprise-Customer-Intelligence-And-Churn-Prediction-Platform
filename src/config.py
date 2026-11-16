from pathlib import Path



BASE_DIR = Path(__file__).resolve().parent.parent

RAW_PATH = BASE_DIR / "data" / "raw" / "telco_churn.csv"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "reports"


# The Telco dataset has no real subscription date, so we derive one:
# subscription_start = SNAPSHOT_DATE - tenure. 
SNAPSHOT_DATE = "2019-09-30"
MAX_TENURE = 120                            # months; anything above is treated as impossible
CUSTOMER_ID_PATTERN = r"^\d{4}-[A-Z]{5}$"   # e.g. 7590-VHVEG


# Raw column name -> clean snake_case name
COLUMN_MAP = {
    "customerID": "customer_id", 
    "gender": "gender", 
    "SeniorCitizen": "senior_citizen",
    "Partner": "partner", 
    "Dependents": "dependents", 
    "tenure": "tenure",
    "PhoneService": "phone_service", 
    "MultipleLines": "multiple_lines",
    "InternetService": "internet_service", 
    "OnlineSecurity": "online_security",
    "OnlineBackup": "online_backup", 
    "DeviceProtection": "device_protection",
    "TechSupport": "tech_support", 
    "StreamingTV": "streaming_tv",
    "StreamingMovies": "streaming_movies", 
    "Contract": "contract_type",
    "PaperlessBilling": "paperless_billing", 
    "PaymentMethod": "payment_method",
    "MonthlyCharges": "monthly_charges", 
    "TotalCharges": "total_charges", 
    "Churn": "churn",
}

NUMERIC_COLS = ["tenure", "monthly_charges", "total_charges"]

YES_NO = {"Yes", "No"}
NO_INTERNET = YES_NO | {"No internet service"}


# Every categorical column and the values it is allowed to contain
ALLOWED_VALUES = {
    "gender": {"Male", "Female"},
    "senior_citizen": {"0", "1"},
    "partner": YES_NO,
    "dependents": YES_NO,
    "phone_service": YES_NO,
    "multiple_lines": YES_NO | {"No phone service"},
    "internet_service": {"DSL", "Fiber optic", "No"},
    "online_security": NO_INTERNET,
    "online_backup": NO_INTERNET,
    "device_protection": NO_INTERNET,
    "tech_support": NO_INTERNET,
    "streaming_tv": NO_INTERNET,
    "streaming_movies": NO_INTERNET,
    "contract_type": {"Month-to-month", "One year", "Two year"},
    "paperless_billing": YES_NO,
    "payment_method": {
        "Electronic check", 
        "Mailed check",
        "Bank transfer (automatic)", 
        "Credit card (automatic)"
    },
    "churn": YES_NO,
}

CATEGORICAL_COLS = list(ALLOWED_VALUES)

ADDON_COLS = [
    "online_security", 
    "online_backup", 
    "device_protection",
    "tech_support", 
    "streaming_tv", 
    "streaming_movies"
]
