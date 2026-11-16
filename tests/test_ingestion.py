import pandas as pd
from src.ingestion.clean import add_subscription_start, clean_text, convert_types, repair_total_charges
from src.ingestion.validate import run_checks, split_valid_rejected



BASE = dict(
    customer_id="7590-VHVEG", 
    gender="Female", 
    senior_citizen="0",
    partner="Yes",
    dependents="No", 
    tenure="1", 
    phone_service="No", 
    multiple_lines="No phone service",
    internet_service="DSL", 
    online_security="No", 
    online_backup="Yes",
    device_protection="No", 
    tech_support="No",
    streaming_tv="No", 
    streaming_movies="No",
    contract_type="Month-to-month", 
    paperless_billing="Yes",
    payment_method="Electronic check", 
    monthly_charges="29.85",
    total_charges="29.85", 
    churn="No"
)


def run_rows(*rows):
    df = pd.DataFrame(list(rows)).astype(str)
    text_df = clean_text(df)
    typed, type_errors = convert_types(text_df)
    typed, _ = repair_total_charges(typed)
    typed = add_subscription_start(typed)
    return split_valid_rejected(typed, run_checks(typed, type_errors), text_df)


def test_valid_row_passes():
    valid, rejected = run_rows(BASE)
    assert len(valid) == 1 and rejected.empty


def test_duplicate_id_rejected():
    valid, rejected = run_rows(BASE, BASE)
    assert len(valid) == 1
    assert "duplicate_customer_id" in rejected["rejection_reasons"].iloc[0]


def test_negative_tenure_rejected():
    _, rejected = run_rows({**BASE, "tenure": "-3"})
    assert "invalid_tenure" in rejected["rejection_reasons"].iloc[0]


def test_non_numeric_charge_rejected():
    _, rejected = run_rows({**BASE, "monthly_charges": "abc"})
    assert "invalid_type_monthly_charges" in rejected["rejection_reasons"].iloc[0]


def test_blank_total_charges_for_new_customer_is_repaired():
    valid, rejected = run_rows({**BASE, "tenure": "0", "total_charges": " "})
    assert len(valid) == 1 and valid["total_charges"].iloc[0] == 0


def test_addon_without_internet_is_inconsistent():
    _, rejected = run_rows({**BASE, "internet_service": "No", "online_security": "Yes"})
    assert "inconsistent_online_security" in rejected["rejection_reasons"].iloc[0]


