"""
Train, compare, calibrate, pick a threshold, evaluate once, and save the churn model.
"""

import hashlib
import json
import time
from datetime import datetime, timezone

import joblib
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_validate, train_test_split

from src.analysis.charts import save
from src.config import PROCESSED_DIR, REPORTS_DIR
from src.db.experiments import log_experiments
from src.ml import business, evaluate as ev, plots
from src.ml.pipeline import build_pipeline, candidate_models
from src.ml.report import write_model_report
from src.ml.settings import (CAPACITY_SHARE, CHURN_DEFINITION, CONTACT_COST, CV_FOLDS, DATA_PATH,
                             EXCLUDED_SENSITIVE, HORIZON_MONTHS, INPUT_FEATURES, LEAKAGE_COLUMNS,
                             MODEL_MARGIN, MODEL_REPORT_DIR, MODEL_VERSION, MODELS_DIR,
                             MONITORED_GROUPS, NON_PREDICTIVE_COLUMNS, RANDOM_STATE,
                             SUCCESS_RATE, TARGET, TEST_SIZE)



def main():
    start = time.time()
    MODELS_DIR.mkdir(exist_ok=True)
    MODEL_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- 1. load data + leakage guard -------------------------------------------------
    df = pd.read_csv(DATA_PATH)
    df[TARGET] = (df["churn"] == "Yes").astype(int)
    dataset_version = hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()[:12]
    assert not set(INPUT_FEATURES) & set(LEAKAGE_COLUMNS), "A leakage column is in the features!"

    # ---- 2. split FIRST, before anything is fitted ----------------------------------------
    X, y = df[INPUT_FEATURES], df[TARGET]
    X_train, X_test, y_train, y_test, _, g_test, id_train, id_test = train_test_split(
        X, y, df[MONITORED_GROUPS], df["customer_id"],
        test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    pd.concat([
        pd.DataFrame({"customer_id": id_train, "split": "train"}),
        pd.DataFrame({"customer_id": id_test, "split": "test"})
    ]).to_csv(PROCESSED_DIR / "train_test_split.csv", index=False)

    # ---- 3. compare candidate models with cross-validation (training data only) -----------
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scoring = {
        "roc_auc": "roc_auc", 
        "pr_auc": "average_precision",
        "precision": "precision", 
        "recall": "recall", 
        "f1": "f1"
    }
    
    rows = []
    for name, clf in candidate_models().items():
        print(f"Cross-validating: {name} ...")
        res = cross_validate(build_pipeline(clf), X_train, y_train, cv=cv, scoring=scoring)
        row = {"model": name, "fit_seconds": round(float(res["fit_time"].mean()), 2)}
        for m in scoring:
            row[f"{m}_mean"] = round(float(res[f"test_{m}"].mean()), 4)
            row[f"{m}_std"] = round(float(res[f"test_{m}"].std()), 4)
        rows.append(row)
    cv_df = pd.DataFrame(rows)
    print(cv_df[["model", "roc_auc_mean", "pr_auc_mean", "precision_mean", "recall_mean", "f1_mean"]])

    # ---- 4. choose the model (prefer the simple baseline unless the gain is real) --------
    base_row, best_row = cv_df.iloc[0], cv_df.loc[cv_df["pr_auc_mean"].idxmax()]
    best_name = best_row["model"]
    reason = f"Highest cross-validated PR-AUC ({best_row['pr_auc_mean']:.3f})."
    
    if best_name != base_row["model"] and best_row["pr_auc_mean"] - base_row["pr_auc_mean"] < MODEL_MARGIN:
        reason = (f"{best_name} scored highest but beat the baseline by less than {MODEL_MARGIN} PR-AUC, "
                  "so the simpler, more explainable baseline was kept.")
        best_name = base_row["model"]
    print(f"Selected model: {best_name}. {reason}")

    # ---- 5. calibrate + out-of-fold probabilities for threshold selection ----------------
    def calibrated():
        return CalibratedClassifierCV(
            estimator=clone(build_pipeline(candidate_models()[best_name])),
            method="sigmoid", 
            cv=CV_FOLDS
        )

    print("Calculating out-of-fold probabilities for threshold selection ...")
    oof = cross_val_predict(calibrated(), X_train, y_train, cv=cv, method="predict_proba")[:, 1]
    value_train = X_train["monthly_charges"].to_numpy() * HORIZON_MONTHS
    table = business.threshold_table(y_train, oof, value_train)
    threshold = business.choose_threshold(table)

    sensitivity = pd.DataFrame([
        {
            "contact_cost": cc, 
            "success_rate": sr,
            "chosen_threshold": business.choose_threshold(
                business.threshold_table(y_train, oof, value_train, contact_cost=cc, success_rate=sr)
            )
        }
        for cc in (15, 30, 60) for sr in (0.15, 0.25, 0.40)
    ])

    # ---- 6. final fit on the training set, ONE evaluation on the test set ---------------
    final = calibrated().fit(X_train, y_train)
    proba_test = final.predict_proba(X_test)[:, 1]
    value_test = X_test["monthly_charges"].to_numpy() * HORIZON_MONTHS

    test_at_t = ev.evaluate(y_test, proba_test, threshold)
    test_at_05 = ev.evaluate(y_test, proba_test, 0.5)
    biz = business.business_outcome(y_test, proba_test, value_test, threshold)
    # What would contacting the same NUMBER of customers at random be worth?
    random_net = biz["contacted_share"] * (
        SUCCESS_RATE * value_test[y_test.to_numpy() == 1].sum() - CONTACT_COST * len(y_test)
    )

    subgroups = ev.group_report(g_test, y_test, proba_test, threshold, MONITORED_GROUPS)
    importance = ev.feature_importance(final, X_test, y_test)
    lr_pipe = build_pipeline(candidate_models()[cv_df.iloc[0]["model"]]).fit(X_train, y_train)
    logistic = ev.logistic_explanation(lr_pipe)

    keys = ["threshold", "roc_auc", "pr_auc", "brier", "precision", "recall", "f1", "tn", "fp", "fn", "tp"]
    compare = pd.DataFrame([
        {"setting": "chosen threshold", **{k: test_at_t[k] for k in keys}},
        {"setting": "default 0.5", **{k: test_at_05[k] for k in keys}}
    ]).round(3)

    # ---- 7. save tables, charts, model, metadata --------------------------------------------
    cv_df.to_csv(MODEL_REPORT_DIR / "model_comparison.csv", index=False)
    table.to_csv(MODEL_REPORT_DIR / "threshold_analysis.csv", index=False)
    sensitivity.to_csv(MODEL_REPORT_DIR / "threshold_sensitivity.csv", index=False)
    subgroups.to_csv(MODEL_REPORT_DIR / "subgroup_check.csv", index=False)
    importance.to_csv(MODEL_REPORT_DIR / "feature_importance.csv", index=False)
    logistic.to_csv(MODEL_REPORT_DIR / "logistic_coefficients.csv", index=False)

    save(plots.comparison_fig(cv_df), "model_comparison", MODEL_REPORT_DIR)
    save(plots.roc_fig(y_test, proba_test), "roc_curve", MODEL_REPORT_DIR)
    save(plots.pr_fig(y_test, proba_test), "pr_curve", MODEL_REPORT_DIR)
    save(plots.calibration_fig(y_test, proba_test), "calibration", MODEL_REPORT_DIR)
    save(plots.threshold_fig(table, threshold, CAPACITY_SHARE), "threshold_selection", MODEL_REPORT_DIR)
    save(plots.confusion_fig(
        test_at_t["tn"], 
        test_at_t["fp"], 
        test_at_t["fn"], 
        test_at_t["tp"]
        ),
        "confusion_matrix", MODEL_REPORT_DIR
    )
    save(plots.importance_fig(importance), "feature_importance", MODEL_REPORT_DIR)

    joblib.dump(final, MODELS_DIR / f"churn_pipeline_{MODEL_VERSION}.joblib", compress=3)
    
    meta = {
        "model_version": MODEL_VERSION, "model_name": best_name, "selection_reason": reason,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": dataset_version, "dataset_rows": int(len(df)),
        "train_rows": int(len(X_train)), "test_rows": int(len(X_test)),
        "churn_definition": CHURN_DEFINITION, "input_features": INPUT_FEATURES,
        "excluded_columns": {"leakage": LEAKAGE_COLUMNS, "sensitive": EXCLUDED_SENSITIVE,
                             "non_predictive": NON_PREDICTIVE_COLUMNS},
        "calibration": "sigmoid (Platt), 5-fold", "threshold": threshold,
        "business_assumptions": {"horizon_months": HORIZON_MONTHS, "contact_cost": CONTACT_COST,
                                 "success_rate": SUCCESS_RATE, "capacity_share": CAPACITY_SHARE},
        "test_metrics_at_threshold": test_at_t,
        "sklearn_version": sklearn.__version__, "random_state": RANDOM_STATE,
    }

    (MODELS_DIR / f"model_metadata_{MODEL_VERSION}.json").write_text(json.dumps(meta, indent=2))

    write_model_report({
        "cv": cv_df[["model", "roc_auc_mean", "pr_auc_mean", "precision_mean", "recall_mean",
                     "f1_mean", "fit_seconds"]],
        "best_name": best_name, "reason": reason, "threshold": threshold, "sensitivity": sensitivity,
        "compare": compare, "test": test_at_t, "business": biz, "random_net": random_net,
        "subgroups": subgroups, "importance": importance, "logistic": logistic,
        "n_train": len(X_train), "n_test": len(X_test),
        "train_churn_pct": 100 * y_train.mean(), "test_churn_pct": 100 * y_test.mean(),
    })

    # ---- 8. log the experiment in the database (never block training if it fails) ------------
    try:
        exp = [{"model_name": r["model"], "model_version": MODEL_VERSION,
                "dataset_version": dataset_version,
                "metrics": {**{k: v for k, v in r.items() if k != "model"}, "stage": "cross_validation"},
                "is_selected": False} for r in rows]
        exp.append({"model_name": f"{best_name} (calibrated, held-out test)",
                    "model_version": MODEL_VERSION, "dataset_version": dataset_version,
                    "metrics": {**test_at_t, "stage": "test"}, "is_selected": True})
        log_experiments(exp)
    except Exception as e:
        print(f"WARNING: could not log experiments to the database: {e}")

    print(f"\nDone in {time.time() - start:.0f}s. Model v{MODEL_VERSION[1:]} saved. "
          f"Threshold {threshold:.2f} | test ROC-AUC {test_at_t['roc_auc']:.3f} | "
          f"PR-AUC {test_at_t['pr_auc']:.3f} | recall {test_at_t['recall']:.2f} | "
          f"precision {test_at_t['precision']:.2f}")




if __name__ == "__main__":
    main()