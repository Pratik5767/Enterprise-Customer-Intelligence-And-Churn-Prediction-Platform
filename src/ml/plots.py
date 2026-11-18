import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.calibration import calibration_curve
from sklearn.metrics import precision_recall_curve, roc_curve



def comparison_fig(cv):
    fig = px.bar(
        cv, x="model", y="pr_auc_mean", error_y="pr_auc_std", text="pr_auc_mean", 
        title="Cross-validated PR-AUC by model (training data, mean ± std)"
    )
    fig.update_traces(texttemplate="%{text:.3f}")
    return fig


def roc_fig(y, proba):
    fpr, tpr, _ = roc_curve(y, proba)
    fig = go.Figure()
    fig.add_scatter(x=fpr, y=tpr, mode="lines", name="Model")
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random guess", line=dict(dash="dash"))
    fig.update_layout(title="ROC curve (test set)", xaxis_title="False positive rate",
                      yaxis_title="True positive rate")
    return fig


def pr_fig(y, proba):
    precision, recall, _ = precision_recall_curve(y, proba)
    fig = go.Figure()
    fig.add_scatter(x=recall, y=precision, mode="lines", name="Model")
    fig.add_hline(y=float(np.mean(y)), line_dash="dash", annotation_text="Baseline = churn rate")
    fig.update_layout(title="Precision-recall curve (test set)", xaxis_title="Recall",
                      yaxis_title="Precision")
    return fig


def calibration_fig(y, proba, bins=10):
    actual, predicted = calibration_curve(y, proba, n_bins=bins, strategy="quantile")
    fig = go.Figure()
    fig.add_scatter(x=predicted, y=actual, mode="lines+markers", name="Model")
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfectly calibrated",
                    line=dict(dash="dash"))
    fig.update_layout(title="Calibration: predicted probability vs actual churn rate (test set)",
                      xaxis_title="Average predicted probability", yaxis_title="Actual churn rate")
    return fig


def threshold_fig(table, chosen, capacity_share):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_scatter(x=table["threshold"], y=table["net_benefit"], name="Net benefit",
                    secondary_y=False)
    fig.add_scatter(x=table["threshold"], y=100 * table["contacted_share"],
                    name="% of customers contacted", secondary_y=True)
    fig.add_scatter(x=table["threshold"], y=[100 * capacity_share] * len(table), mode="lines",
                    line=dict(dash="dot"), name="Team capacity", secondary_y=True)
    fig.add_vline(x=chosen, line_dash="dash", annotation_text=f"Chosen: {chosen:.2f}")
    fig.update_layout(title="Threshold selection (out-of-fold predictions on training data)",
                      xaxis_title="Probability threshold")
    fig.update_yaxes(title_text="Net benefit (money units)", secondary_y=False)
    fig.update_yaxes(title_text="% of customers contacted", secondary_y=True)
    return fig


def confusion_fig(tn, fp, fn, tp):
    return px.imshow([[tn, fp], [fn, tp]], text_auto=True, color_continuous_scale="Blues",
                     x=["Predicted: stay", "Predicted: churn"],
                     y=["Actually stayed", "Actually churned"],
                     title="Confusion matrix at the chosen threshold (test set)")


def importance_fig(imp, top=12):
    d = imp.head(top).sort_values("importance_mean")
    return px.bar(d, x="importance_mean", y="feature", orientation="h", error_x="importance_std",
                  title="Permutation importance (drop in PR-AUC when the column is shuffled)")

