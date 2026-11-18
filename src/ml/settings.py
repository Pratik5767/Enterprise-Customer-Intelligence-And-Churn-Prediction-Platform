from src.config import BASE_DIR, PROCESSED_DIR, REPORTS_DIR



DATA_PATH = PROCESSED_DIR / "customers_clean.csv"
MODELS_DIR = BASE_DIR / "models"
MODEL_REPORT_DIR = REPORTS_DIR / "model"

MODEL_VERSION = "v1"
RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
MODEL_MARGIN = 0.01     # a complex model must beat the baseline's PR-AUC by this much to be chosen


# 1. churn definition
TARGET = "churn_flag"

CHURN_DEFINITION = (
    "Churn = 1 if the customer left the company during the observation window (original `Churn` "
    "column = 'Yes'); 0 if they were still subscribed. The model is meant to score a currently "
    "active customer, using only account information known at scoring time (contract, services, "
    "billing, tenure so far), to estimate the chance they leave in the next billing period. "
    "Dataset caveat: this is a single snapshot, so for customers who already left, tenure and "
    "total charges describe the account at the moment they left."
)


# 2. features
NUMERIC_FEATURES = ["tenure", "monthly_charges", "total_charges"]

CATEGORICAL_FEATURES = [
    "senior_citizen", "partner", "dependents", "phone_service", "multiple_lines",
    "internet_service", "online_security", "online_backup", "device_protection",
    "tech_support", "streaming_tv", "streaming_movies", "contract_type",
    "paperless_billing", "payment_method",
]

INPUT_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES                    # what a new record must contain

ENGINEERED_NUMERIC = ["num_addons", "num_services", "charges_per_service"]  # created inside the pipeline

# Columns that must NEVER be model inputs
LEAKAGE_COLUMNS = ["churn", "churn_flag", "subscription_status"]            # derived directly from the outcome

NON_PREDICTIVE_COLUMNS = [
    "customer_id", "subscription_start", "is_outlier", "monthly_charges_outlier", "total_charges_outlier"
]

EXCLUDED_SENSITIVE = ["gender"]                                             # not used by the model...

MONITORED_GROUPS = ["gender", "senior_citizen"]                             # ...but checked for unfair outcomes


# 3. business assumptions
# PLACEHOLDERS. Replace them with figures from the business and write the source in your report.
HORIZON_MONTHS = 12      # a lost customer's value = monthly charges x this many months
CONTACT_COST = 30.0      # cost of one retention outreach (agent time + offer), in money units
SUCCESS_RATE = 0.25      # share of would-be churners that an outreach actually retains
CAPACITY_SHARE = 0.25    # the team can contact at most this share of customers per cycle

