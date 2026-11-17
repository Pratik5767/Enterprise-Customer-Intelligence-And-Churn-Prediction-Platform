# EDA Report (auto-generated numbers)

Dataset: 7,038 validated customers. Overall churn rate: **26.5%** (1,867 churned, 5,171 retained).

> Everything below is an **observed association**. Nothing here proves that one factor causes churn.

## 1. Churn by segment

### contract_type
Within **contract_type**, observed churn ranges from 2.8% (Two year, n=1,695) to 42.7% (Month-to-month, n=3,872).

| contract_type | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| Month-to-month | 3872 | 1653 | 42.7 | 41.1 | 44.3 |
| One year | 1471 | 166 | 11.3 | 9.8 | 13.0 |
| Two year | 1695 | 48 | 2.8 | 2.1 | 3.7 |

### tenure_bucket
Within **tenure_bucket**, observed churn ranges from 9.5% (49-72, n=2,239) to 47.4% (0-12, n=2,183).

| tenure_bucket | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| 0-12 | 2183 | 1035 | 47.4 | 45.3 | 49.5 |
| 13-24 | 1024 | 294 | 28.7 | 26.0 | 31.6 |
| 25-48 | 1592 | 325 | 20.4 | 18.5 | 22.5 |
| 49-72 | 2239 | 213 | 9.5 | 8.4 | 10.8 |

### payment_method
Within **payment_method**, observed churn ranges from 15.2% (Credit card (automatic), n=1,522) to 45.3% (Electronic check, n=2,363).

| payment_method | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| Bank transfer (automatic) | 1543 | 258 | 16.7 | 14.9 | 18.7 |
| Credit card (automatic) | 1522 | 232 | 15.2 | 13.5 | 17.1 |
| Electronic check | 2363 | 1070 | 45.3 | 43.3 | 47.3 |
| Mailed check | 1610 | 307 | 19.1 | 17.2 | 21.1 |

### internet_service
Within **internet_service**, observed churn ranges from 7.4% (No, n=1,526) to 41.9% (Fiber optic, n=3,095).

| internet_service | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| DSL | 2417 | 458 | 18.9 | 17.4 | 20.6 |
| Fiber optic | 3095 | 1296 | 41.9 | 40.1 | 43.6 |
| No | 1526 | 113 | 7.4 | 6.2 | 8.8 |

### paperless_billing
Within **paperless_billing**, observed churn ranges from 16.3% (No, n=2,870) to 33.5% (Yes, n=4,168).

| paperless_billing | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| No | 2870 | 469 | 16.3 | 15.0 | 17.7 |
| Yes | 4168 | 1398 | 33.5 | 32.1 | 35.0 |

### senior_citizen
Within **senior_citizen**, observed churn ranges from 23.6% (No, n=5,896) to 41.7% (Yes, n=1,142).

| senior_citizen | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| No | 5896 | 1391 | 23.6 | 22.5 | 24.7 |
| Yes | 1142 | 476 | 41.7 | 38.9 | 44.6 |

### partner
Within **partner**, observed churn ranges from 19.7% (Yes, n=3,401) to 32.9% (No, n=3,637).

| partner | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| No | 3637 | 1198 | 32.9 | 31.4 | 34.5 |
| Yes | 3401 | 669 | 19.7 | 18.4 | 21.0 |

### dependents
Within **dependents**, observed churn ranges from 15.5% (Yes, n=2,110) to 31.3% (No, n=4,928).

| dependents | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| No | 4928 | 1541 | 31.3 | 30.0 | 32.6 |
| Yes | 2110 | 326 | 15.5 | 14.0 | 17.1 |

### gender
Within **gender**, observed churn ranges from 26.2% (Male, n=3,552) to 26.9% (Female, n=3,486).

| gender | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| Female | 3486 | 938 | 26.9 | 25.5 | 28.4 |
| Male | 3552 | 929 | 26.2 | 24.7 | 27.6 |

### tech_support
Within **tech_support**, observed churn ranges from 7.4% (No internet service, n=1,526) to 41.6% (No, n=3,469).

| tech_support | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| No | 3469 | 1444 | 41.6 | 40.0 | 43.3 |
| No internet service | 1526 | 113 | 7.4 | 6.2 | 8.8 |
| Yes | 2043 | 310 | 15.2 | 13.7 | 16.8 |

### online_security
Within **online_security**, observed churn ranges from 7.4% (No internet service, n=1,526) to 41.8% (No, n=3,496).

| online_security | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| No | 3496 | 1460 | 41.8 | 40.1 | 43.4 |
| No internet service | 1526 | 113 | 7.4 | 6.2 | 8.8 |
| Yes | 2016 | 294 | 14.6 | 13.1 | 16.2 |

### monthly_charge_band
Within **monthly_charge_band**, observed churn ranges from 11.2% (Q1 (lowest), n=1,761) to 37.5% (Q3, n=1,756).

| monthly_charge_band | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| Q1 (lowest) | 1761 | 198 | 11.2 | 9.9 | 12.8 |
| Q2 | 1763 | 433 | 24.6 | 22.6 | 26.6 |
| Q3 | 1756 | 658 | 37.5 | 35.2 | 39.8 |
| Q4 (highest) | 1758 | 578 | 32.9 | 30.7 | 35.1 |

## 2. Service usage (internet customers only)
Customers without internet have no add-ons by definition, so they are excluded here.

| num_addons | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| 0.0 | 692.0 | 361.0 | 52.2 | 48.4 | 55.9 |
| 1.0 | 965.0 | 442.0 | 45.8 | 42.7 | 49.0 |
| 2.0 | 1031.0 | 369.0 | 35.8 | 32.9 | 38.8 |
| 3.0 | 1117.0 | 306.0 | 27.4 | 24.9 | 30.1 |
| 4.0 | 852.0 | 190.0 | 22.3 | 19.6 | 25.2 |
| 5.0 | 571.0 | 71.0 | 12.4 | 10.0 | 15.4 |
| 6.0 | 284.0 | 15.0 | 5.3 | 3.2 | 8.5 |

## 3. Payment method within month-to-month contracts only
Controls for contract type, so any remaining difference is not just a contract effect.

| payment_method | customers | churned | churn_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|
| Bank transfer (automatic) | 589 | 201 | 34.1 | 30.4 | 38.0 |
| Credit card (automatic) | 543 | 178 | 32.8 | 29.0 | 36.8 |
| Electronic check | 1848 | 993 | 53.7 | 51.5 | 56.0 |
| Mailed check | 892 | 281 | 31.5 | 28.5 | 34.6 |

## 4. Numeric features: churned vs retained

| feature | churned_mean | retained_mean | churned_median | retained_median |
|---|---|---|---|---|
| tenure | 18.0 | 37.6 | 10.0 | 38.0 |
| monthly_charges | 74.5 | 61.3 | 79.6 | 64.4 |
| total_charges | 1533.3 | 2550.7 | 706.6 | 1679.4 |
| num_services | 3.6 | 3.8 | 3.0 | 4.0 |

## 5. Monthly charges linked to churned customers

- Total monthly charges (all customers): 455,862.95
- Monthly charges of churned customers: 139,006.3 (30.5% of the total)

## 6. Strength of association with churn

| feature | cramers_v | p_value | strength |
|---|---|---|---|
| contract_type | 0.41 | 1.53e-257 | strong |
| tenure_bucket | 0.348 | 8.02e-185 | strong |
| online_security | 0.348 | 2.45e-185 | strong |
| tech_support | 0.343 | 2.43e-180 | strong |
| internet_service | 0.322 | 1.43e-159 | strong |
| payment_method | 0.303 | 4.06e-140 | strong |
| monthly_charge_band | 0.226 | 1.81e-77 | moderate |
| paperless_billing | 0.191 | 4.73e-58 | moderate |
| dependents | 0.164 | 3.67e-43 | moderate |
| senior_citizen | 0.151 | 8.31e-37 | moderate |
| partner | 0.15 | 2.12e-36 | moderate |
| gender | 0.009 | 4.74e-01 | weak |
