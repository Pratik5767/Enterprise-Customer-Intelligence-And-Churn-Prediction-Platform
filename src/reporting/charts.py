import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots



def style(fig, height=380):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=50, r=20, t=60, b=50))
    return fig


def risk_palette(names: list) -> dict:
    """
    Green for the lowest band through red for the highest, for any number of bands.
    """
    
    n = len(names)
    if n == 1:
        return {names[0]: "#888888"}
    colors = px.colors.sample_colorscale("RdYlGn_r", [i / (n - 1) for i in range(n)])
    return dict(zip(names, colors))


def risk_mix_fig(scored, col, risk_order, title, order=None):
    cats = {"risk_level": risk_order}
    if order:
        cats[col] = order
    fig = px.histogram(scored, x=col, color="risk_level", barnorm="percent", category_orders=cats,
                       color_discrete_map=risk_palette(risk_order), title=title)
    fig.update_yaxes(title_text="% of active customers")
    fig.update_xaxes(title_text="")
    return style(fig)


def revenue_band_fig(by_band, risk_order):
    fig = px.bar(by_band, x="risk_level", y="expected_revenue_at_risk", color="risk_level", text="customers",
                 category_orders={"risk_level": risk_order}, color_discrete_map=risk_palette(risk_order),
                 title="Expected annual revenue at risk by risk band (labels = customers)")
    fig.update_layout(showlegend=False)
    fig.update_yaxes(title_text="Expected annual revenue at risk")
    fig.update_xaxes(title_text="")
    return style(fig)


def priority_fig(priority):
    fig = px.bar(priority, x="expected_revenue_at_risk", y="priority_segment", orientation="h", text="customers",
                 title="Expected annual revenue at risk by priority segment (labels = customers)")
    fig.update_yaxes(autorange="reversed", title_text="")
    fig.update_xaxes(title_text="Expected annual revenue at risk")
    return style(fig)


def concentration_fig(curve):
    step = max(1, len(curve) // 400)
    c = pd.concat([curve.iloc[::step], curve.iloc[[-1]]]).drop_duplicates()
    fig = go.Figure()
    fig.add_scatter(x=100 * c["customer_share"], y=100 * c["loss_share"], mode="lines",
                    name="Customers ranked by expected loss")
    fig.add_scatter(x=[0, 100], y=[0, 100], mode="lines", name="Even spread", line=dict(dash="dash"))
    fig.update_layout(title="How concentrated is the expected revenue at risk?",
                      xaxis_title="% of active customers (highest expected loss first)",
                      yaxis_title="% of expected revenue at risk")
    return style(fig)


def trend_fig(trend, high_name):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_scatter(x=trend["scored_on"], y=100 * trend["avg_probability"], mode="lines+markers",
                    name="Average predicted probability (%)", customdata=trend[["customers"]].to_numpy(),
                    hovertemplate="%{x|%Y-%m-%d}<br>%{y:.1f}%<br>%{customdata[0]:,} customers<extra></extra>",
                    secondary_y=False)
    fig.add_scatter(x=trend["scored_on"], y=trend["pct_high"], mode="lines+markers",
                    name=f"% at or above the {high_name} cutoff", secondary_y=True)
    fig.update_yaxes(title_text="Average probability (%)", secondary_y=False)
    fig.update_yaxes(title_text=f"% at or above the {high_name} cutoff", secondary_y=True)
    fig.update_layout(title="Predicted churn risk across scoring runs")
    return style(fig)

