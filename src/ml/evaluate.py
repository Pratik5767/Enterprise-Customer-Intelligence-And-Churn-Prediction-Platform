import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score



def evaluate(y_true, proba, threshold) -> dict:
    pred = (np.asarray(proba) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    
    return {
        "threshold": float(threshold),
        "roc_auc": float(roc_auc_score(y_true, proba)),
        "pr_auc": float(average_precision_score(y_true, proba)),
        "brier": float(brier_score_loss(y_true, proba)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred)),
        "f1": float(f1_score(y_true, pred)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def group_report(groups: pd.DataFrame, y_true, proba, threshold, group_cols) -> pd.DataFrame:
    """Same outcome measures per subgroup. Large gaps are a warning sign for bias."""
    
    y = np.asarray(y_true)
    pred = (np.asarray(proba) >= threshold).astype(int)
    rows = []
    
    for col in group_cols:
        values = groups[col].to_numpy()
        for v in pd.unique(values):
            m = values == v
            tp = int(((pred == 1) & (y == 1) & m).sum())
            
            rows.append({
                "group": col, 
                "value": v, 
                "customers": int(m.sum()),
                "actual_churn_pct": round(100 * float(y[m].mean()), 1),
                "flagged_pct": round(100 * float(pred[m].mean()), 1),
                "recall_pct": round(100 * tp / max(int(((y == 1) & m).sum()), 1), 1),
                "precision_pct": round(100 * tp / max(int(((pred == 1) & m).sum()), 1), 1),
            })
    
    return pd.DataFrame(rows)


def feature_importance(model, X, y, n_repeats=10, seed=42) -> pd.DataFrame:
    """Shuffle one input column at a time; the bigger the drop in PR-AUC, the more the model relies on it."""
    
    r = permutation_importance(model, X, y, scoring="average_precision", n_repeats=n_repeats, random_state=seed)
    out = pd.DataFrame({
        "feature": X.columns, 
        "importance_mean": r.importances_mean,
        "importance_std": r.importances_std
    })

    return out.sort_values("importance_mean", ascending=False).reset_index(drop=True)


def logistic_explanation(fitted_pipeline) -> pd.DataFrame:
    """Direction and size of each feature's effect in the baseline model."""
    
    names = fitted_pipeline.named_steps["prep"].get_feature_names_out()
    coef = fitted_pipeline.named_steps["clf"].coef_[0]
    out = pd.DataFrame({
        "feature": names, 
        "coefficient": coef, 
        "odds_ratio": np.exp(coef)
    })
    out["feature"] = out["feature"].str.replace(r"^(num|cat)__", "", regex=True)
    order = out["coefficient"].abs().sort_values(ascending=False).index
    
    return out.loc[order].reset_index(drop=True)

