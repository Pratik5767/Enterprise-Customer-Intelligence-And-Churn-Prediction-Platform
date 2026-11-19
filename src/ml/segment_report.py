import pandas as pd
import plotly.express as px

from src.analysis.charts import save
from src.analysis.run_eda import md_table
from src.config import REPORTS_DIR
from src.ml import segmentation as seg



SEG_DIR = REPORTS_DIR / "segmentation"


def summarize(df: pd.DataFrame, by, high_name: str) -> pd.DataFrame:
    d = df.assign(is_high=df["risk_level"].astype(str) == high_name)
    out = (
        d.groupby(by, observed=True)
            .agg(
                customers=("customer_id", "size"),
                avg_probability=("churn_probability", "mean"),
                pct_high_risk=("is_high", "mean"),
                flagged=("flagged_for_review", "sum"),
                monthly_billing=("monthly_charges", "sum"),
                revenue_at_risk=("expected_revenue_at_risk", "sum")
            ).reset_index()
        )
    out["share_pct"] = (100 * out["customers"] / len(df)).round(1)
    out["avg_probability"] = out["avg_probability"].round(3)
    out["pct_high_risk"] = (100 * out["pct_high_risk"]).round(1)
    out["monthly_billing"] = out["monthly_billing"].round(0)
    out["revenue_at_risk"] = out["revenue_at_risk"].round(0)
    return out


def make_report(out: pd.DataFrame, monitor: pd.DataFrame, cfg: dict, meta: dict, ref_prob: float) -> None:
    SEG_DIR.mkdir(parents=True, exist_ok=True)
    risk_order = seg.ordered_names(cfg["risk_bands"])
    value_order = seg.ordered_names(cfg["value_tiers"])
    high, low, top_value = risk_order[-1], risk_order[0], value_order[-1]
    horizon = meta["business_assumptions"]["horizon_months"]
    n = len(out)

    # ---------------- tables ----------------
    risk = summarize(out, "risk_level", high)
    priority = summarize(out, ["priority_rank", "priority_segment"], high)
    dims = {
        "Tenure": "tenure_segment", 
        "Subscription type (contract)": "subscription_type",
        "Spending (monthly-charge tier)": "value_tier", 
        "Service usage": "usage_band"
    }
    dim_tables = {title: summarize(out, col, high) for title, col in dims.items()}
    cross = (
        pd.crosstab(
            out["risk_level"].astype(str),
            out["flagged_for_review"].map({True: "flagged", False: "not flagged"})
        ).reindex(risk_order).fillna(0).astype(int).reset_index()
    )

    hv = out[(out["value_tier"].astype(str) == top_value) & (out["risk_level"].astype(str) != low)]
    hv = hv.sort_values("expected_revenue_at_risk", ascending=False)
    hv_cols = [
        "customer_id", "churn_probability", "risk_level", "monthly_charges", "annual_value",
        "expected_revenue_at_risk", "tenure", "subscription_type", "top_risk_factors_text", 
        "review_action"
    ]
    hv[hv_cols].to_csv(SEG_DIR / "high_value_at_risk.csv", index=False)

    chk = out[["risk_level", "flagged_for_review", "churn_probability"]].join(monitor)
    chk["is_high"] = chk["risk_level"].astype(str) == high
    
    fair = pd.concat([
        chk.groupby(col).agg(
            customers=("churn_probability", "size"),
            avg_probability=("churn_probability", "mean"),
            pct_high_risk=("is_high", "mean"),
            pct_flagged=("flagged_for_review", "mean")
        ).reset_index().rename(columns={col: "value"}).assign(group=col)
        for col in monitor.columns
    ])
    fair["avg_probability"] = fair["avg_probability"].round(3)
    fair["pct_high_risk"] = (100 * fair["pct_high_risk"]).round(1)
    fair["pct_flagged"] = (100 * fair["pct_flagged"]).round(1)
    fair = fair[["group", "value", "customers", "avg_probability", "pct_high_risk", "pct_flagged"]]

    top = out.head(15)[[
        "customer_id", "churn_probability", "risk_level", "value_tier",
        "monthly_charges", "expected_revenue_at_risk", "top_risk_factors_text"
    ]].copy()
    
    top["churn_probability"] = top["churn_probability"].round(3)

    # ---------------- charts ----------------
    fig = px.histogram(
        out, 
        x="churn_probability", 
        nbins=40, 
        title="Distribution of churn probability (active customers)"
    )

    for name in risk_order[1:]:
        fig.add_vline(x=cfg["risk_bands"][name], line_dash="dash", annotation_text=f"{name} starts")
    
    fig.add_vline(x=meta["threshold"], line_dash="dot", line_color="red", annotation_text="Review threshold")
    save(fig, "risk_distribution", SEG_DIR)

    orders = {
        "tenure_segment": seg.ordered_names(cfg["tenure_segments"]),
        "value_tier": value_order, 
        "usage_band": seg.ordered_names(cfg["usage_bands"])
    }
    
    for title, col in dims.items():
        fig = px.histogram(
            out, 
            x=col, 
            color="risk_level", 
            barnorm="percent",
            category_orders={
                "risk_level": risk_order,
                **({col: orders[col]} if col in orders else {})
            },
            title=f"Risk level mix by {title.lower()}"
        )
        
        fig.update_yaxes(title_text="% of customers")
        save(fig, f"risk_by_{col}", SEG_DIR)

    grid = (pd.crosstab(out["risk_level"].astype(str), out["value_tier"].astype(str))
              .reindex(index=risk_order[::-1], columns=value_order).fillna(0).astype(int))
    
    save(
        px.imshow(
            grid, 
            text_auto=True, 
            color_continuous_scale="Reds", 
            aspect="auto",
            labels=dict(x="Value tier", y="Risk level", color="Customers"),
            title="Customers by risk level and value tier"
        ), 
        "risk_value_matrix", 
        SEG_DIR
    )

    fig = px.bar(
        priority, 
        x="revenue_at_risk", 
        y="priority_segment", 
        orientation="h", 
        text="customers",
        title="Expected annual revenue at risk by priority segment (labels = customers)"
    )
    
    fig.update_yaxes(autorange="reversed")
    save(fig, "revenue_at_risk_by_priority", SEG_DIR)

    # ---------------- markdown ----------------
    L = ["# Customer Risk Segmentation Report (auto-generated numbers)", "",
         f"> {seg.PREDICTION_NOTICE}", "", "## 1. Overview", "",
         f"- Customers scored (currently active): {n:,}",
         f"- Model: {meta['model_name']} ({meta['model_version']}), scored on {out['prediction_date'].iloc[0][:10]}",
         f"- Review threshold from Module 3: {meta['threshold']:.2f}, which flags "
         f"{int(out['flagged_for_review'].sum()):,} customers ({100 * out['flagged_for_review'].mean():.1f}%) for review",
         f"- A typical customer (median / most common training profile) has an estimated probability of "
         f"{ref_prob:.1%}. Explanations compare each customer with that profile.",
         f"- Expected annual revenue at risk (probability x {horizon} months of charges): "
         f"{out['expected_revenue_at_risk'].sum():,.0f}",
         f"- Risk bands (lower bounds): {cfg['risk_bands']}", "",
         "## 2. Risk bands", "", md_table(risk), "",
         "### Review flag vs risk band", "",
         "The flag comes from Module 3's cost- and capacity-based threshold; bands are descriptive. "
         "If you want them to agree, set the High band's lower bound to the threshold in `config/segmentation.json`.", "",
         md_table(cross), "",
         "## 3. Priority segments (risk x value)", "", md_table(priority), "",
         f"The full list of **{top_value}** customers at elevated risk is in "
         f"`reports/segmentation/high_value_at_risk.csv` ({len(hv):,} customers).", ""]

    for i, (title, t) in enumerate(dim_tables.items(), start=4):
        L += [f"## {i}. By {title.lower()}", "", md_table(t), ""]
    L += ["## 8. Top 15 customers to review first", "", md_table(top), "",
          "## 9. Example explanations", ""]
    for _, r in out.head(3).iterrows():
        L.append(f"- **{r['customer_id']}** (probability {r['churn_probability']:.0%}) | raising risk: "
                 f"{r['top_risk_factors_text']} | lowering risk: {r['top_protective_factors_text']}")
    L += ["", "## 10. Fairness check on the segments", "",
          "Compare how often each group lands in the high band or on the review list. Large gaps need investigation.",
          "", md_table(fair), "",
          "## 11. How to read the explanations", "",
          "- Each effect is the change in the model's estimate (percentage points) when that group of fields is "
          "replaced by the typical customer's values. Positive = raises this customer's risk.",
          "- Effects are one at a time and do not add up exactly, because factors interact.",
          "- They describe what the model learned. They are not proof that changing a factor would change behaviour.",
          "- Senior-citizen status is used by the model but deliberately not displayed as a reason."]
    (REPORTS_DIR / "segmentation_report.md").write_text("\n".join(L), encoding="utf-8")

    