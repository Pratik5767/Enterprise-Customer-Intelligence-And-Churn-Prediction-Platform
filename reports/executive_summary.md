# Executive Summary: Customer Churn and Retention

*Data as of 2026-11-19 | model Logistic Regression (baseline) (v1) | generated 2026-11-24 10:46 UTC*

> A risk score is an estimate of likelihood, not a confirmed decision by the customer to leave. Scores are for human review and prioritisation only; they must not trigger automatic account actions.

## At a glance

26.5% of customers in the data have churned (1,869 of 7,043). Among the 5,171 active customers with a current score, 5.0% sit in the High risk band and carry 20.8% of an expected $821,210 annual revenue at risk.

| measure | value |
|---|---|
| Total customers | 7,043 |
| Churned (observed to date) | 1,869 (26.5%) |
| Retained (active) | 5,174 |
| Active customers with a current score | 5,171 |
| In the High risk band | 260 (5.0% of scored) |
| Flagged for review | 633 |
| Monthly billing in the High band | $21,013 |
| Expected annual revenue at risk | $821,210 |
| Monthly billing of churned customers | $139,131 (30.5% of total) |

## Data notes

- 3 active customers have no stored score and are left out of the risk sections. Run: python -m src.ml.segment_run
- SYNTHETIC DEMO HISTORY is included in the trend section. Those scoring runs are fake and exist only to test the charts.

## Key findings

1. **Portfolio.** 7,043 customers: 5,174 retained and 1,869 churned (26.5%). Churned customers accounted for $139,131 of monthly billing (30.5% of the total).
2. **Contract type.** Observed churn ranges from 2.8% (Two year, n=1,695) to 42.7% (Month-to-month, n=3,875).
3. **Tenure (months).** Observed churn ranges from 9.5% (49-72, n=2,239) to 47.4% (0-12, n=2,186).
4. **Revenue at risk.** Among active customers with a current score, expected annual revenue at risk is $821,210 (churn probability x 12 months of charges; about 22% of their annual billing). The High band holds 5.0% of those customers but 20.8% of that amount.
5. **Concentration.** The 10% of active customers with the highest expected loss hold 39% of the expected revenue at risk; the top 20% hold 63%.
6. **Top-priority segment.** 79 customers are in the highest review-priority tier (Critical: high value, high risk); together they pay $7,684 per month.
7. **Where elevated risk concentrates.** Highest shares of active customers in the High band: Payment method = Electronic check: 17.9% (n=1,293); Tenure (months) = 0-12: 15.8% (n=1,148); Internet service = Fiber optic: 13.5% (n=1,799). Segments overlap, so these are not independent groups.
8. SYNTHETIC DEMO HISTORY: **Trend over time.** Average predicted churn probability moved from 14.1% (2026-05-23, 5,171 customers scored) to 18.5% (2026-11-19, 5,171 scored); the share at or above the High cutoff moved from 2.8% to 5.0%.
9. **Movement since the previous run.** Of 5,171 customers scored in both runs, 0 rose by 10+ points and 0 fell by 10+ points.
10. **Retention campaigns.** No real campaigns have been recorded yet. (1 synthetic demo campaign(s) are excluded from this summary.)

## Recommended areas for investigation

These are questions raised by the data, not conclusions.

1. Why is observed churn higher on Month-to-month contracts (42.7%) than on Two year contracts (2.8%)? Contract type, tenure and price overlap, so a randomised test (for example, offering a contract upgrade to a random half of eligible customers) would be needed to learn whether changing the contract changes retention.
2. What happens in the first year? Customers with 0-12 months of tenure show 47.4% observed churn against 26.5% overall. Review onboarding, early billing experience and first-year offers, and check how many of these customers are also on month-to-month contracts.
3. Why do customers with internet service = Fiber optic show higher observed churn (41.9% vs 26.5% overall, n=3,096)? Price, service quality and customer mix are all possible explanations; this data cannot separate them.
4. Why do customers with payment method = Electronic check show higher observed churn (45.3% vs 26.5% overall, n=2,365)? Price, service quality and customer mix are all possible explanations; this data cannot separate them.
5. A small group of customers holds a large share of expected revenue at risk (top 10% = 39%). Check whether account-level review of these customers is practical before planning broad outreach.
6. Run the next retention campaign with a randomised holdout group, so its effect on retention can be measured. Without one, results can only be described.
7. Once later customer-status data exists, compare earlier predictions with what customers actually did, to check that the model's probabilities still match reality.

## Caveats

- A risk score is an estimate of likelihood, not a confirmed decision by the customer to leave. Scores are for human review and prioritisation only; they must not trigger automatic account actions.
- Observed churn is the share of customers in the dataset who have already left (a single snapshot). It is not a rate per month or quarter, and the data holds no churn dates, so observed churn cannot be tracked over time. The trend shown is the trend in predicted risk across scoring runs.
- Expected revenue at risk = churn probability x 12 months of current monthly charges. It assumes a lost customer is not replaced and ignores discounting. The probabilities come from a model trained on this same customer base, so scores for customers that were in the training data are somewhat optimistic.
- Segment comparisons are descriptive. Segments overlap (for example contract type and tenure), and none of these differences shows what would happen if a customer's contract, price or service changed.
- If the customer data is a public or synthetic sample, results illustrate the platform and may not generalise to a real business.