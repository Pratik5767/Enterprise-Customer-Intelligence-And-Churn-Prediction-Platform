import pandas as pd
import plotly.express as px
from src.analysis.stats import churn_by



def churn_bar(df, col, title, overall):
    t = churn_by(df, col)
    
    fig = px.bar(
        t, 
        x=col, 
        y="churn_rate_pct", 
        text="churn_rate_pct",
        error_y=t["ci_high_pct"] - t["churn_rate_pct"],
        error_y_minus=t["churn_rate_pct"] - t["ci_low_pct"],
        hover_data=["customers", "churned"], 
        title=title,
        labels={"churn_rate_pct": "Churn rate (%)"},
    )

    fig.update_traces(texttemplate="%{text}%")
    fig.add_hline(y=overall, line_dash="dash", annotation_text=f"Group average {overall:.1f}%")
    fig.update_xaxes(type="category")
    fig.update_yaxes(range=[0, min(100, float(t["ci_high_pct"].max()) + 8)])
    
    return fig


def distribution_by_churn(df, col, title, nbins=40):
    # histnorm="percent" scales each group to sum to 100%, so a smaller group
    # (churned) is still visible next to a larger one (retained)
    return px.histogram(
        df, 
        x=col, 
        color="churn", 
        barmode="overlay", 
        opacity=0.6,
        nbins=nbins, 
        histnorm="percent", 
        title=title,
        labels={"churn": "Churned?"}
    )


def box_by_churn(df, col, title):
    return px.box(
        df, 
        x="churn", 
        y=col, 
        points=False, 
        title=title,
        labels={"churn": "Churned?"}
    )


def contract_tenure_heatmap(df, min_n=30):
    keys = dict(index="contract_type", columns="tenure_bucket", values="churn_flag", observed=True)
    counts = df.pivot_table(aggfunc="count", **keys)
    rates = (
        df.pivot_table(aggfunc="mean", **keys) * 100
    ).where(counts >= min_n).round(1)
    
    return px.imshow(
        rates, 
        text_auto=".1f", 
        color_continuous_scale="Reds", 
        aspect="auto",
        title=f"Churn % by contract and tenure (cells with n < {min_n} hidden)",
        labels=dict(x="Tenure (months)", y="Contract", color="Churn %")
    )


def correlation_heatmap(df):
    cols = ["tenure", "monthly_charges", "total_charges", "num_services", "senior_flag", "churn_flag"]
    corr = df[cols].corr().round(2)
    
    return px.imshow(
        corr, 
        text_auto=True, 
        zmin=-1, 
        zmax=1, 
        color_continuous_scale="RdBu_r",
        title="Correlation matrix (Pearson)"
    )


def association_chart(assoc: pd.DataFrame):
    return px.bar(
        assoc.sort_values("cramers_v"), 
        x="cramers_v", 
        y="feature", 
        orientation="h",
        title="Association with churn (Cramér's V; higher = stronger association)",
        labels={"cramers_v": "Cramér's V", "feature": ""}
    )


def save(fig, name, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    fig.write_html(out_dir / f"{name}.html", include_plotlyjs="cdn")
    
    try:
        fig.write_image(out_dir / f"{name}.png", width=900, height=500, scale=2)
    except Exception:
        pass