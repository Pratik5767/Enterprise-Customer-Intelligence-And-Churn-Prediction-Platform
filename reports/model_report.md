# Model Comparison & Evaluation Report (v1, auto-generated numbers)

## 1. Churn definition and prediction point

Churn = 1 if the customer left the company during the observation window (original `Churn` column = 'Yes'); 0 if they were still subscribed. The model is meant to score a currently active customer, using only account information known at scoring time (contract, services, billing, tenure so far), to estimate the chance they leave in the next billing period. Dataset caveat: this is a single snapshot, so for customers who already left, tenure and total charges describe the account at the moment they left.

## 2. Data split

- Training set: 5,630 customers (26.5% churn)
- Test set (used once, at the end): 1,408 customers (26.6% churn)
- Stratified split with a fixed random seed; one row per customer, so no customer is in both sets.

## 3. Model comparison (5-fold cross-validation on the training set)

| model | roc_auc_mean | pr_auc_mean | precision_mean | recall_mean | f1_mean | fit_seconds |
|---|---|---|---|---|---|---|
| Logistic Regression (baseline) | 0.8424 | 0.6507 | 0.5132 | 0.8044 | 0.6264 | 0.09 |
| Random Forest | 0.8437 | 0.6588 | 0.5418 | 0.7589 | 0.632 | 1.13 |
| Gradient Boosting | 0.8401 | 0.6568 | 0.5222 | 0.7555 | 0.6171 | 0.89 |

**Selected: Logistic Regression (baseline).** Random Forest scored highest but beat the baseline by less than 0.01 PR-AUC, so the simpler, more explainable baseline was kept.

## 4. Threshold selection

Assumptions (placeholders, editable in `src/ml/settings.py`): customer value = monthly charges x 12 months; one outreach costs 30.0; an offer retains 25% of would-be churners; the team can contact at most 25% of customers per cycle.

**Chosen threshold: 0.46**, the highest net benefit on out-of-fold predictions that does not exceed team capacity.

Sensitivity of the chosen threshold to the cost assumptions:

| contact_cost | success_rate | chosen_threshold |
|---|---|---|
| 15.0 | 0.15 | 0.46 |
| 15.0 | 0.25 | 0.46 |
| 15.0 | 0.4 | 0.46 |
| 30.0 | 0.15 | 0.46 |
| 30.0 | 0.25 | 0.46 |
| 30.0 | 0.4 | 0.46 |
| 60.0 | 0.15 | 0.46 |
| 60.0 | 0.25 | 0.46 |
| 60.0 | 0.4 | 0.46 |

## 5. Test-set performance (final calibrated model)

| setting | threshold | roc_auc | pr_auc | brier | precision | recall | f1 | tn | fp | fn | tp |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chosen threshold | 0.46 | 0.848 | 0.656 | 0.134 | 0.644 | 0.604 | 0.623 | 909 | 125 | 148 | 226 |
| default 0.5 | 0.5 | 0.848 | 0.656 | 0.134 | 0.674 | 0.559 | 0.611 | 933 | 101 | 165 | 209 |

### What the errors mean in business terms (test set, using the assumptions above)

- **False negatives (missed churners): 148** customers, about 112,556 of 12-month revenue that was never targeted.
- **False positives (unnecessary outreach): 125** customers, about 3,750 of wasted outreach cost.
- Expected campaign result: revenue saved 55,357 minus campaign cost 10,530 = **net benefit 44,827**. Contacting the same number of customers at random would give about 10,285.

## 6. Subgroup check (potential bias)

Large gaps in recall or flagged rate between groups need investigation.

| group | value | customers | actual_churn_pct | flagged_pct | recall_pct | precision_pct |
|---|---|---|---|---|---|---|
| gender | Female | 677 | 28.1 | 26.4 | 60.5 | 64.2 |
| gender | Male | 731 | 25.2 | 23.5 | 60.3 | 64.5 |
| senior_citizen | No | 1178 | 23.3 | 19.9 | 54.7 | 63.8 |
| senior_citizen | Yes | 230 | 43.5 | 50.4 | 76.0 | 65.5 |

## 7. What the model relies on

Permutation importance on the test set (association with the model's predictions, not proof of cause):

| feature | importance_mean | importance_std |
|---|---|---|
| tenure | 0.2616 | 0.0098 |
| total_charges | 0.0577 | 0.0122 |
| contract_type | 0.0526 | 0.012 |
| internet_service | 0.0472 | 0.0106 |
| tech_support | 0.0107 | 0.0061 |
| phone_service | 0.009 | 0.0102 |
| streaming_movies | 0.0081 | 0.0044 |
| paperless_billing | 0.0075 | 0.0066 |
| online_security | 0.0074 | 0.0071 |
| multiple_lines | 0.0063 | 0.0054 |

Baseline logistic regression, largest effects (odds ratio above 1 raises churn odds):

| feature | coefficient | odds_ratio |
|---|---|---|
| tenure | -1.31 | 0.27 |
| contract_type_Two year | -0.816 | 0.442 |
| contract_type_Month-to-month | 0.645 | 1.906 |
| total_charges | 0.64 | 1.897 |
| internet_service_Fiber optic | 0.401 | 1.493 |
| internet_service_DSL | -0.379 | 0.685 |
| monthly_charges | -0.318 | 0.727 |
| payment_method_Electronic check | 0.304 | 1.355 |
| paperless_billing_No | -0.248 | 0.781 |
| payment_method_Mailed check | -0.215 | 0.807 |
| multiple_lines_No | -0.21 | 0.81 |
| phone_service_Yes | -0.199 | 0.82 |

## 8. Limitations

See `reports/model_limitations.md` (written by hand).