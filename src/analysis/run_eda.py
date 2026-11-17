from src.analysis import charts, stats
from src.analysis.prep import load_clean
from src.config import REPORTS_DIR



SEGMENT_COLS = [
    "contract_type", 
    "tenure_bucket", 
    "payment_method", 
    "internet_service",
    "paperless_billing", 
    "senior_citizen", 
    "partner", 
    "dependents", 
    "gender",
    "tech_support", 
    "online_security", 
    "monthly_charge_band"
]

CHARTS = {
    "contract_type": "Churn rate by contract type",
    "tenure_bucket": "Churn rate by tenure (months)",
    "payment_method": "Churn rate by payment method",
    "internet_service": "Churn rate by internet service",
    "tech_support": "Churn rate by tech support (support-service proxy)",
    "senior_citizen": "Churn rate by senior-citizen status",
    "monthly_charge_band": "Churn rate by monthly-charge quartile",
}


def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def main():
    out = REPORTS_DIR / "eda"
    df = load_clean()
    n = len(df) 
    churned = int(df["churn_flag"].sum())
    overall = 100 * churned / n

    inet = df[df["internet_service"] != "No"]            # customers who have internet
    m2m = df[df["contract_type"] == "Month-to-month"]    # month-to-month customers only

    seg = {c: stats.churn_by(df, c) for c in SEGMENT_COLS}
    addons = stats.churn_by(inet, "num_addons")
    pay_m2m = stats.churn_by(m2m, "payment_method")
    assoc = stats.association_with_churn(df, SEGMENT_COLS)
    nums = stats.numeric_summary(df, ["tenure", "monthly_charges", "total_charges", "num_services"])
    rev = stats.revenue_summary(df)


    # ---- charts ----
    for col, title in CHARTS.items():
        charts.save(
            charts.churn_bar(df, col, title, overall), 
            f"churn_by_{col}", 
            out
        )
    
    charts.save(
        charts.churn_bar(
            inet, 
            "num_addons",
            "Churn by number of add-on services (internet customers only)",
            100 * inet["churn_flag"].mean()
        ), 
        "churn_by_num_addons", 
        out
    )

    charts.save(
        charts.churn_bar(
            m2m, 
            "payment_method",
            "Churn by payment method (month-to-month customers only)",
            100 * m2m["churn_flag"].mean()
        ), 
        "churn_by_payment_within_m2m", 
        out
    )
    
    charts.save(
        charts.distribution_by_churn(
            df, 
            "monthly_charges",
            "Monthly charges: churned vs retained (each group sums to 100%)"
        ),
        "dist_monthly_charges", 
        out
    )
    
    charts.save(
        charts.distribution_by_churn(
            df, 
            "tenure",
            "Tenure: churned vs retained (each group sums to 100%)", 
            nbins=36
        ),
        "dist_tenure", 
        out
    )
    
    charts.save(
        charts.box_by_churn(
            df, 
            "total_charges", 
            "Total charges: churned vs retained"
        ),
        "box_total_charges", 
        out
    )
    
    charts.save(charts.contract_tenure_heatmap(df), "heatmap_contract_tenure", out)
    charts.save(charts.correlation_heatmap(df), "correlation_matrix", out)
    charts.save(charts.association_chart(assoc), "association_with_churn", out)


    # ---- auto-generated factual report ----
    cols = lambda c: [c, "customers", "churned", "churn_rate_pct", "ci_low_pct", "ci_high_pct"]
    
    L = ["# EDA Report (auto-generated numbers)", "",
         f"Dataset: {n:,} validated customers. Overall churn rate: **{overall:.1f}%** "
         f"({churned:,} churned, {n - churned:,} retained).", "",
         "> Everything below is an **observed association**. Nothing here proves that one factor "
         "causes churn.", "", "## 1. Churn by segment", ""]
    
    for c, t in seg.items():
        L += [f"### {c}", stats.contrast_sentence(t, c), "", md_table(t[cols(c)]), ""]

    L += ["## 2. Service usage (internet customers only)",
          "Customers without internet have no add-ons by definition, so they are excluded here.", "",
          md_table(addons[cols("num_addons")]), "",
          "## 3. Payment method within month-to-month contracts only",
          "Controls for contract type, so any remaining difference is not just a contract effect.", "",
          md_table(pay_m2m[cols("payment_method")]), "",
          "## 4. Numeric features: churned vs retained", "", md_table(nums), "",
          "## 5. Monthly charges linked to churned customers", "",
          f"- Total monthly charges (all customers): {rev['total_monthly_charges']:,}",
          f"- Monthly charges of churned customers: {rev['monthly_charges_of_churned_customers']:,} "
          f"({rev['share_of_monthly_charges_pct']}% of the total)", "",
          "## 6. Strength of association with churn", "",
          md_table(assoc.assign(p_value=assoc["p_value"].map(lambda v: f"{v:.2e}"))), ""]
    
    (REPORTS_DIR / "eda_report.md").write_text("\n".join(L), encoding="utf-8")
    
    print(f"EDA complete: {n:,} customers, churn {overall:.1f}%. See reports/eda_report.md and reports/eda/")




if __name__ == "__main__":
    main()

