# Data Quality Report

- Rows received: 7044
- Valid rows: 7038
- Rejected rows: 6 (0.09%)
- Exact duplicate rows: 1
- Duplicate customer IDs: 1
- Blank TotalCharges repaired to 0 (tenure = 0): 11

## Missing values by column (before repair)
- customer_id: 1
- total_charges: 11

## Rejection reasons
- missing_customer_id: 1
- duplicate_customer_id: 1
- invalid_type_monthly_charges: 1
- invalid_tenure: 1
- subscription_start_in_future: 1
- invalid_contract_type: 1
- inconsistent_online_security: 1
- inconsistent_online_backup: 1
- inconsistent_device_protection: 1
- inconsistent_tech_support: 1
- inconsistent_streaming_tv: 1
- inconsistent_streaming_movies: 1

## Outliers flagged (kept in data)
- monthly_charges_outlier: 0
- total_charges_outlier: 0