# Customer Risk Segmentation Report (auto-generated numbers)

> A risk score is an estimate of likelihood, not a confirmed decision by the customer to leave. Scores are for human review and prioritisation only; they must not trigger automatic account actions.

## 1. Overview

- Customers scored (currently active): 5,171
- Model: Logistic Regression (baseline) (v1), scored on 2026-11-19
- Review threshold from Module 3: 0.46, which flags 633 customers (12.2%) for review
- A typical customer (median / most common training profile) has an estimated probability of 45.8%. Explanations compare each customer with that profile.
- Expected annual revenue at risk (probability x 12 months of charges): 821,210
- Risk bands (lower bounds): {'Low': 0.0, 'Medium': 0.3, 'High': 0.6}

## 2. Risk bands

| risk_level | customers | avg_probability | pct_high_risk | flagged | monthly_billing | revenue_at_risk | share_pct |
|---|---|---|---|---|---|---|---|
| Low | 3931 | 0.091 | 0.0 | 0 | 223121.0 | 270391.0 | 76.0 |
| Medium | 980 | 0.433 | 0.0 | 373 | 72722.0 | 379719.0 | 19.0 |
| High | 260 | 0.678 | 100.0 | 260 | 21013.0 | 171100.0 | 5.0 |

### Review flag vs risk band

The flag comes from Module 3's cost- and capacity-based threshold; bands are descriptive. If you want them to agree, set the High band's lower bound to the threshold in `config/segmentation.json`.

| risk_level | flagged | not flagged |
|---|---|---|
| Low | 0 | 3931 |
| Medium | 373 | 607 |
| High | 260 | 0 |

## 3. Priority segments (risk x value)

| priority_rank | priority_segment | customers | avg_probability | pct_high_risk | flagged | monthly_billing | revenue_at_risk | share_pct |
|---|---|---|---|---|---|---|---|---|
| 1 | Critical: high value, high risk | 79 | 0.679 | 100.0 | 79 | 7684.0 | 62492.0 | 1.5 |
| 2 | Priority: high value, medium risk | 319 | 0.433 | 0.0 | 121 | 31584.0 | 163726.0 | 6.2 |
| 2 | Priority: mid value, high risk | 136 | 0.677 | 100.0 | 136 | 10826.0 | 87935.0 | 2.6 |
| 3 | Standard: low value, high risk | 45 | 0.681 | 100.0 | 45 | 2503.0 | 20672.0 | 0.9 |
| 3 | Standard: mid value, medium risk | 280 | 0.452 | 0.0 | 138 | 22449.0 | 121709.0 | 5.4 |
| 4 | Healthy: low value, low risk | 2459 | 0.081 | 0.0 | 0 | 86959.0 | 93008.0 | 47.6 |
| 4 | Healthy: mid value, low risk | 679 | 0.089 | 0.0 | 0 | 54565.0 | 58759.0 | 13.1 |
| 4 | Monitor: low value, medium risk | 381 | 0.419 | 0.0 | 114 | 18689.0 | 94284.0 | 7.4 |
| 4 | Protect: high value, low risk | 793 | 0.122 | 0.0 | 0 | 81597.0 | 118625.0 | 15.3 |

The full list of **High value** customers at elevated risk is in `reports/segmentation/high_value_at_risk.csv` (398 customers).

## 4. By tenure

| tenure_segment | customers | avg_probability | pct_high_risk | flagged | monthly_billing | revenue_at_risk | share_pct |
|---|---|---|---|---|---|---|---|
| New (0-12 months) | 1148 | 0.343 | 15.8 | 350 | 53646.0 | 274691.0 | 22.2 |
| Developing (13-24 months) | 730 | 0.26 | 7.9 | 156 | 39748.0 | 162104.0 | 14.1 |
| Established (25-48 months) | 1267 | 0.176 | 1.7 | 117 | 77532.0 | 215826.0 | 24.5 |
| Loyal (49+ months) | 2026 | 0.075 | 0.0 | 10 | 145931.0 | 168589.0 | 39.2 |

## 5. By subscription type (contract)

| subscription_type | customers | avg_probability | pct_high_risk | flagged | monthly_billing | revenue_at_risk | share_pct |
|---|---|---|---|---|---|---|---|
| Month-to-month | 2219 | 0.344 | 11.7 | 628 | 136417.0 | 636022.0 | 42.9 |
| One year | 1305 | 0.114 | 0.0 | 5 | 81599.0 | 138871.0 | 25.2 |
| Two year | 1647 | 0.028 | 0.0 | 0 | 98841.0 | 46317.0 | 31.9 |

## 6. By spending (monthly-charge tier)

| value_tier | customers | avg_probability | pct_high_risk | flagged | monthly_billing | revenue_at_risk | share_pct |
|---|---|---|---|---|---|---|---|
| Low value | 2885 | 0.135 | 1.6 | 159 | 108150.0 | 207964.0 | 55.8 |
| Mid value | 1095 | 0.255 | 12.4 | 274 | 87841.0 | 268403.0 | 21.2 |
| High value | 1191 | 0.242 | 6.6 | 200 | 120865.0 | 344843.0 | 23.0 |

## 7. By service usage

| usage_band | customers | avg_probability | pct_high_risk | flagged | monthly_billing | revenue_at_risk | share_pct |
|---|---|---|---|---|---|---|---|
| Light (1-2 services) | 1809 | 0.143 | 4.9 | 174 | 50246.0 | 134818.0 | 35.0 |
| Moderate (3-4 services) | 1241 | 0.295 | 10.0 | 303 | 81182.0 | 316366.0 | 24.0 |
| Heavy (5+ services) | 2121 | 0.157 | 2.2 | 156 | 185429.0 | 370025.0 | 41.0 |

## 8. Top 15 customers to review first

| customer_id | churn_probability | risk_level | value_tier | monthly_charges | expected_revenue_at_risk | top_risk_factors_text |
|---|---|---|---|---|---|---|
| 5150-ITWWB | 0.826 | High | High value | 94.85 | 940.61 | Tenure (3 months) +20.7 pts; Phone service (phone: Yes, multiple lines: Yes) +3.2 pts; Other add-on services (2 of 4 active) +2.6 pts |
| 3292-PBZEJ | 0.687 | High | High value | 111.4 | 917.85 | Tenure (11 months) +21.1 pts; Phone service (phone: Yes, multiple lines: Yes) +4.6 pts; Other add-on services (4 of 4 active) +4.2 pts |
| 5956-YHHRX | 0.711 | High | High value | 104.35 | 890.19 | Tenure (21 months) +15.2 pts; Phone service (phone: Yes, multiple lines: Yes) +4.4 pts |
| 3320-VEOYC | 0.776 | High | High value | 95.6 | 889.65 | Tenure (14 months) +15.6 pts; Phone service (phone: Yes, multiple lines: Yes) +3.8 pts; Other add-on services (2 of 4 active) +3.1 pts |
| 6350-XFYGW | 0.78 | High | High value | 94.75 | 887.31 | Tenure (4 months) +22.4 pts; Other add-on services (3 of 4 active) +2.1 pts |
| 8161-QYMTT | 0.774 | High | High value | 94.1 | 874.57 | Tenure (7 months) +20.7 pts; Phone service (phone: Yes, multiple lines: Yes) +3.8 pts; Other add-on services (2 of 4 active) +3.3 pts |
| 7225-CBZPL | 0.764 | High | High value | 94.8 | 868.56 | Tenure (17 months) +14.2 pts; Phone service (phone: Yes, multiple lines: Yes) +3.9 pts; Other add-on services (2 of 4 active) +3.3 pts |
| 0916-QOFDP | 0.754 | High | High value | 95.8 | 866.45 | Tenure (14 months) +16.8 pts; Phone service (phone: Yes, multiple lines: Yes) +4.0 pts; Other add-on services (2 of 4 active) +3.3 pts |
| 5935-FCCNB | 0.765 | High | High value | 94.2 | 864.53 | Tenure (17 months) +14.5 pts; Phone service (phone: Yes, multiple lines: Yes) +3.9 pts; Other add-on services (2 of 4 active) +3.3 pts |
| 3452-GWUIN | 0.754 | High | High value | 94.95 | 859.34 | Tenure (19 months) +13.3 pts; Phone service (phone: Yes, multiple lines: Yes) +4.0 pts; Other add-on services (2 of 4 active) +3.4 pts |
| 5995-SNNEW | 0.685 | High | High value | 104.45 | 858.33 | Tenure (23 months) +12.4 pts; Phone service (phone: Yes, multiple lines: Yes) +4.6 pts |
| 9290-SHCMB | 0.734 | High | High value | 96.85 | 852.59 | Tenure (13 months) +17.9 pts; Other add-on services (3 of 4 active) +2.1 pts |
| 7668-XCFYV | 0.767 | High | High value | 92.55 | 852.05 | Tenure (17 months) +14.4 pts; Phone service (phone: Yes, multiple lines: Yes) +3.9 pts; Other add-on services (2 of 4 active) +3.5 pts |
| 7145-FEJWU | 0.673 | High | High value | 105.3 | 850.66 | Tenure (12 months) +20.6 pts; Phone service (phone: Yes, multiple lines: Yes) +4.6 pts |
| 6734-GMPVK | 0.666 | High | High value | 105.3 | 841.18 | Tenure (5 months) +24.8 pts; Phone service (phone: Yes, multiple lines: Yes) +4.7 pts |

## 9. Example explanations

- **5150-ITWWB** (probability 83%) | raising risk: Tenure (3 months) +20.7 pts; Phone service (phone: Yes, multiple lines: Yes) +3.2 pts; Other add-on services (2 of 4 active) +2.6 pts | lowering risk: none stands out
- **3292-PBZEJ** (probability 69%) | raising risk: Tenure (11 months) +21.1 pts; Phone service (phone: Yes, multiple lines: Yes) +4.6 pts; Other add-on services (4 of 4 active) +4.2 pts | lowering risk: Tech support / online security (tech support: Yes, online security: No) -6.2 pts; Monthly charges (111.40) -4.4 pts
- **5956-YHHRX** (probability 71%) | raising risk: Tenure (21 months) +15.2 pts; Phone service (phone: Yes, multiple lines: Yes) +4.4 pts | lowering risk: Monthly charges (104.35) -3.1 pts; Other add-on services (4 of 4 active) -2.0 pts

## 10. Fairness check on the segments

Compare how often each group lands in the high band or on the review list. Large gaps need investigation.

| group | value | customers | avg_probability | pct_high_risk | pct_flagged |
|---|---|---|---|---|---|
| gender | Female | 2548 | 0.185 | 5.1 | 12.8 |
| gender | Male | 2623 | 0.185 | 5.0 | 11.7 |
| senior_citizen | No | 4505 | 0.167 | 3.5 | 9.9 |
| senior_citizen | Yes | 666 | 0.308 | 15.2 | 28.1 |

## 11. How to read the explanations

- Each effect is the change in the model's estimate (percentage points) when that group of fields is replaced by the typical customer's values. Positive = raises this customer's risk.
- Effects are one at a time and do not add up exactly, because factors interact.
- They describe what the model learned. They are not proof that changing a factor would change behaviour.
- Senior-citizen status is used by the model but deliberately not displayed as a reason.