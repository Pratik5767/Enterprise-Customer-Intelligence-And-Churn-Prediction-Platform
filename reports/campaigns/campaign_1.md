# Retention Campaign Report: [SYNTHETIC DEMO] Retention calls 20261120-163429

> **SYNTHETIC DEMO DATA.** Outreach and retention outcomes below were simulated to test the software. They are not real results.

## 1. Campaign

| item | value |
|---|---|
| Type | phone_call |
| Owner | demo.manager@example.com |
| Status | completed |
| Target segment | Critical and Priority customers (Module 4 ranks 1-2) |
| Selection rule | {"priority_ranks": [1, 2]} |
| Start date | 2026-11-20 |
| Retention outcomes due from | 2027-02-18 |
| Design | randomised holdout |
| Holdout share | 25% |
| Cost per contact attempt | 30.0 |
| Incentive cost per accepted offer | 25.0 |
| Fixed cost | 0.0 |

## 2. Outreach and participation

| item | value |
|---|---|
| Customers enrolled | 534 |
| In the campaign group | 400 |
| In the holdout (not contacted) | 134 |
| Contact attempted | 400 |
| Reached | 354 |
| Reach rate (reached / attempted) | 88.5% |
| Unreachable after repeated attempts | 46 |
| Not yet contacted | 0 |
| Overdue follow-ups | 0 |
| Offers accepted | 134 |
| Acceptance rate (accepted / reached) | 37.9% |
| Declined | 86 |

## 3. Costs

| item | value |
|---|---|
| Contact attempts | 666.0 |
| Contact cost | 19980.0 |
| Incentive cost | 3350.0 |
| Fixed cost | 0.0 |
| **Total cost** | 23330.0 |
| Variable cost per customer reached | 65.9 |

## 4. Retention outcomes by group

| group | customers | outcomes_known | coverage_pct | retained | retention_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|---|---|
| treatment | 400 | 400 | 100.0 | 286 | 71.5 | 66.9 | 75.7 |
| control | 134 | 134 | 100.0 | 61 | 45.5 | 37.3 | 54.0 |

## 5. What can and cannot be concluded

**Customers assigned to the campaign were retained at 71.5% versus 45.5% in the randomised holdout group (difference +26.0 points, 95% CI +16.4 to +35.2; n = 400 vs 134). Because customers were assigned at random, this gap is unlikely to be chance and can be attributed to the campaign (measured per customer assigned, whether or not each was reached). Treat this with caution: see the data-quality warnings.**

- Warning: The two groups differ noticeably at enrolment on: Churn probability at enrolment, Tenure (months).
- This is measured per customer *assigned*, including those who could not be reached.
- One campaign in one period is one experiment; repeat it before treating the result as general.

## 6. Money impact

| item | value |
|---|---|
| Additional customers retained (estimate) | 103.9 (95% CI 65.4 to 140.7) |
| Incremental revenue (estimate) | 116,887 |
| Total campaign cost | 23,330 |
| Net benefit (estimate) | 93,557 (range 50,276 to 134,949) |
| Return on cost | 401% |
| Cost per additional customer retained | 224 |

Assumptions: a retained customer is worth 12 months of their monthly charges; customers with unknown outcomes behave like those with known outcomes. If the range includes negative values, the campaign may not have paid for itself.

## 7. Were the groups alike at the start? (randomisation check)

| measure | campaign_group | holdout_group | smd |
|---|---|---|---|
| Churn probability at enrolment | 0.536 | 0.518 | 0.123 |
| Monthly charges | 93.732 | 94.043 | -0.03 |
| Tenure (months) | 25.735 | 29.53 | -0.198 |
| Share on month-to-month | 0.907 | 0.896 | 0.04 |

SMD values above about 0.1 in absolute size mean the groups differ at enrolment.

## 8. Reached vs not reached (descriptive only, not an effect estimate)

| contact | customers | avg_risk_at_enrolment_pct | retention_rate_pct |
|---|---|---|---|
| not reached | 46 | 58.9 | 34.8 |
| reached | 354 | 52.9 | 76.3 |

Compare the starting risk of the two rows. Customers who can be reached are usually different from those who cannot, so a gap in retention here mixes the campaign with that difference. Use section 5 for any statement about the campaign's effect.

## 9. By priority segment (exploratory)

| priority_segment_at_enrollment | campaign_n | holdout_n | campaign_retention_pct | holdout_retention_pct | difference_pts | reliable |
|---|---|---|---|---|---|---|
| Critical: high value, high risk | 59 | 20 | 64.4 | 45.0 | 19.4 | False |
| Priority: high value, medium risk | 239 | 80 | 78.7 | 52.5 | 26.2 | True |
| Priority: mid value, high risk | 102 | 34 | 58.8 | 29.4 | 29.4 | True |

Subgroups are small and many were examined; do not act on a single subgroup result.
