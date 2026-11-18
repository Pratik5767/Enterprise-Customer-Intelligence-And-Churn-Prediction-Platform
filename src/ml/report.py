from src.analysis.run_eda import md_table
from src.ml.settings import CAPACITY_SHARE, CHURN_DEFINITION, CONTACT_COST, HORIZON_MONTHS, MODEL_VERSION, SUCCESS_RATE
from src.config import REPORTS_DIR



def write_model_report(c: dict) -> None:
    t, b = c["test"], c["business"]
    
    L = [
        f"# Model Comparison & Evaluation Report ({MODEL_VERSION}, auto-generated numbers)", "",
        "## 1. Churn definition and prediction point", "", CHURN_DEFINITION, "",
        "## 2. Data split", "",
        f"- Training set: {c['n_train']:,} customers ({c['train_churn_pct']:.1f}% churn)",
        f"- Test set (used once, at the end): {c['n_test']:,} customers ({c['test_churn_pct']:.1f}% churn)",
        "- Stratified split with a fixed random seed; one row per customer, so no customer is in both sets.", "",
        "## 3. Model comparison (5-fold cross-validation on the training set)", "",
        md_table(c["cv"].round(4)), "",
        f"**Selected: {c['best_name']}.** {c['reason']}", "",
        "## 4. Threshold selection", "",
        f"Assumptions (placeholders, editable in `src/ml/settings.py`): customer value = monthly charges x "
        f"{HORIZON_MONTHS} months; one outreach costs {CONTACT_COST}; an offer retains {int(SUCCESS_RATE * 100)}% "
        f"of would-be churners; the team can contact at most {int(CAPACITY_SHARE * 100)}% of customers per cycle.", "",
        f"**Chosen threshold: {c['threshold']:.2f}**, the highest net benefit on out-of-fold predictions "
        "that does not exceed team capacity.", "",
        "Sensitivity of the chosen threshold to the cost assumptions:", "", md_table(c["sensitivity"]), "",
        "## 5. Test-set performance (final calibrated model)", "", md_table(c["compare"]), "",
        "### What the errors mean in business terms (test set, using the assumptions above)", "",
        f"- **False negatives (missed churners): {t['fn']}** customers, about {b['missed_churn_value']:,.0f} "
        f"of {HORIZON_MONTHS}-month revenue that was never targeted.",
        f"- **False positives (unnecessary outreach): {t['fp']}** customers, about "
        f"{b['wasted_contact_cost']:,.0f} of wasted outreach cost.",
        f"- Expected campaign result: revenue saved {b['revenue_saved']:,.0f} minus campaign cost "
        f"{b['campaign_cost']:,.0f} = **net benefit {b['net_benefit']:,.0f}**. Contacting the same number "
        f"of customers at random would give about {c['random_net']:,.0f}.", "",
        "## 6. Subgroup check (potential bias)", "",
        "Large gaps in recall or flagged rate between groups need investigation.", "",
        md_table(c["subgroups"]), "",
        "## 7. What the model relies on", "",
        "Permutation importance on the test set (association with the model's predictions, not proof of cause):", "",
        md_table(c["importance"].head(10).round(4)), "",
        "Baseline logistic regression, largest effects (odds ratio above 1 raises churn odds):", "",
        md_table(c["logistic"].head(12).round(3)), "",
        "## 8. Limitations", "", "See `reports/model_limitations.md` (written by hand).",
    ]

    (REPORTS_DIR / "model_report.md").write_text("\n".join(L), encoding="utf-8")

