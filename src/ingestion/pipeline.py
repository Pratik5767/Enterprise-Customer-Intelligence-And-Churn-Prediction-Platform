from src.config import PROCESSED_DIR, RAW_PATH
from src.db.load import init_db, upsert_customers
from src.ingestion.clean import add_subscription_start, clean_text, convert_types, repair_total_charges, standardize_columns
from src.ingestion.features import prepare_features
from src.ingestion.loader import load_api, load_csv
from src.ingestion.outliers import flag_outliers
from src.ingestion.report import build_summary, write_reports
from src.ingestion.validate import run_checks, split_valid_rejected



def run(source="csv", csv_path=RAW_PATH, api_url=None, save_to_db=True):
    # 1. Load (everything as text)
    raw = load_csv(csv_path) if source == "csv" else load_api(api_url)
    total_rows = len(raw)

    # 2. Standardize names, trim whitespace, blanks -> missing
    text_df = clean_text(standardize_columns(raw))
    missing_before = text_df.isna().sum()
    duplicate_rows = text_df.duplicated().sum()

    # 3. Convert types, repair known quirk, derive subscription date
    typed, type_errors = convert_types(text_df)
    typed, repaired = repair_total_charges(typed)
    typed = add_subscription_start(typed)

    # 4. Validate and split
    checks = run_checks(typed, type_errors)
    valid, rejected = split_valid_rejected(typed, checks, text_df)

    # 5. Outliers: flag, don't remove
    outliers = flag_outliers(valid)
    valid = valid.join(outliers)
    valid["is_outlier"] = outliers.any(axis=1)

    # 6. Final feature typing
    valid = prepare_features(valid)

    # 7. Save outputs
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    valid.to_csv(PROCESSED_DIR / "customers_clean.csv", index=False)
    
    summary = build_summary(total_rows, missing_before, duplicate_rows, repaired, checks, valid, rejected, outliers)
    write_reports(summary, rejected)

    # 8. Store in database
    if save_to_db:
        init_db()
        db_df = valid.copy()
        db_df["subscription_start"] = db_df["subscription_start"].dt.date
        upsert_customers(db_df)

    print(f"Received {total_rows} | valid {len(valid)} | rejected {len(rejected)}")
    return valid, rejected, summary




if __name__ == "__main__":
    run()