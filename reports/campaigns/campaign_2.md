# Retention Campaign Report: [SYNTHETIC DEMO] Retention calls 20261120-163227

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
| Reached | 361 |
| Reach rate (reached / attempted) | 90.2% |
| Unreachable after repeated attempts | 39 |
| Not yet contacted | 0 |
| Overdue follow-ups | 0 |
| Offers accepted | 120 |
| Acceptance rate (accepted / reached) | 33.2% |
| Declined | 117 |

## 3. Costs

| item | value |
|---|---|
| Contact attempts | 669.0 |
| Contact cost | 20070.0 |
| Incentive cost | 3000.0 |
| Fixed cost | 0.0 |
| **Total cost** | 23070.0 |
| Variable cost per customer reached | 63.91 |

## 4. Retention outcomes by group

| group | customers | outcomes_known | coverage_pct | retained | retention_rate_pct | ci_low_pct | ci_high_pct |
|---|---|---|---|---|---|---|---|
| treatment | 400 | 400 | 100.0 | 268 | 67.0 | 62.2 | 71.4 |
| control | 134 | 134 | 100.0 | 60 | 44.8 | 36.6 | 53.2 |

## 5. What can and cannot be concluded

**Customers assigned to the campaign were retained at 67.0% versus 44.8% in the randomised holdout group (difference +22.2 points, 95% CI +12.5 to +31.5; n = 400 vs 134). Because customers were assigned at random, this gap is unlikely to be chance and can be attributed to the campaign (measured per customer assigned, whether or not each was reached).**

- This is measured per customer *assigned*, including those who could not be reached.
- One campaign in one period is one experiment; repeat it before treating the result as general.

## 6. Money impact

| item | value |
|---|---|
| Additional customers retained (estimate) | 88.9 (95% CI 50.1 to 126.0) |
| Incremental revenue (estimate) | 100,296 |
| Total campaign cost | 23,070 |
| Net benefit (estimate) | 77,226 (range 33,488 to 119,114) |
| Return on cost | 335% |
| Cost per additional customer retained | 260 |

Assumptions: a retained customer is worth 12 months of their monthly charges; customers with unknown outcomes behave like those with known outcomes. If the range includes negative values, the campaign may not have paid for itself.

## 7. Were the groups alike at the start? (randomisation check)

| measure | campaign_group | holdout_group | smd |
|---|---|---|---|
| Churn probability at enrolment | 0.531 | 0.533 | -0.019 |
| Monthly charges | 94.037 | 93.131 | 0.088 |
| Tenure (months) | 26.492 | 27.269 | -0.04 |
| Share on month-to-month | 0.902 | 0.91 | -0.027 |

SMD values above about 0.1 in absolute size mean the groups differ at enrolment.

## 8. Reached vs not reached (descriptive only, not an effect estimate)

| contact | customers | avg_risk_at_enrolment_pct | retention_rate_pct |
|---|---|---|---|
| not reached | 39 | 61.8 | 33.3 |
| reached | 361 | 52.1 | 70.6 |

Compare the starting risk of the two rows. Customers who can be reached are usually different from those who cannot, so a gap in retention here mixes the campaign with that difference. Use section 5 for any statement about the campaign's effect.

## 9. By priority segment (exploratory)

| priority_segment_at_enrollment | campaign_n | holdout_n | campaign_retention_pct | holdout_retention_pct | difference_pts | reliable |
|---|---|---|---|---|---|---|
| Critical: high value, high risk | 59 | 20 | 57.6 | 15.0 | 42.6 | False |
| Priority: high value, medium risk | 239 | 80 | 74.9 | 52.5 | 22.4 | True |
| Priority: mid value, high risk | 102 | 34 | 53.9 | 44.1 | 9.8 | True |

Subgroups are small and many were examined; do not act on a single subgroup result.
