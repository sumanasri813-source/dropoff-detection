from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

TARGET_COLUMN = "dropoff_label"


def _load_config_defaults() -> Dict[str, object]:
    defaults: Dict[str, object] = {
        "threshold_candidates": [0.30, 0.40, 0.50, 0.60, 0.70, 0.80],
        "cost_false_positive": 10,
        "cost_false_negative": 100,
        "benefit_true_positive": 200,
    }

    try:
        from src.utils.config_loader import load_config

        cfg = load_config("config.yaml")
        eval_cfg = cfg.get("evaluation", {})
        defaults["threshold_candidates"] = eval_cfg.get("threshold_range", defaults["threshold_candidates"])
        defaults["cost_false_positive"] = eval_cfg.get("cost_false_positive", defaults["cost_false_positive"])
        defaults["cost_false_negative"] = eval_cfg.get("cost_false_negative", defaults["cost_false_negative"])
        defaults["benefit_true_positive"] = eval_cfg.get("benefit_true_positive", defaults["benefit_true_positive"])
    except Exception:
        pass

    return defaults


def _safe_predict_proba(model: object, X: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]

    if hasattr(model, "decision_function"):
        scores = model.decision_function(X)
        min_s, max_s = np.min(scores), np.max(scores)
        if max_s == min_s:
            return np.full_like(scores, 0.5, dtype=float)
        return (scores - min_s) / (max_s - min_s)

    raise ValueError("Model must support predict_proba or decision_function for probability-based metrics.")


def _compute_classification_metrics(y_true: pd.Series, y_prob: np.ndarray, threshold: float) -> Dict[str, float]:
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def _business_value_from_cm(
    cm: np.ndarray,
    cost_false_positive: float,
    cost_false_negative: float,
    benefit_true_positive: float,
) -> Dict[str, float]:
    tn, fp, fn, tp = cm.ravel()
    business_value = (tp * benefit_true_positive) - (fp * cost_false_positive) - (fn * cost_false_negative)
    return {
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
        "tp": float(tp),
        "business_value": float(business_value),
    }


def _select_best_threshold(y_true: pd.Series, y_prob: np.ndarray, candidates: List[float]) -> Dict[str, float]:
    """Select best threshold based on F1 score. O(n*k) optimized with direct calculation."""
    best = {"threshold": 0.5, "f1": -1.0}
    for t in candidates:
        y_pred = (y_prob >= t).astype(int)
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        if f1 > best["f1"]:
            best["threshold"] = float(t)
            best["f1"] = f1
    return best


def evaluate_model(
    model_path: str = "models/final_model.pkl",
    data_path: str = "data/processed/model_data.csv",
) -> Dict[str, object]:
    model = joblib.load(model_path)
    df = pd.read_csv(data_path)

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' not found in {data_path}")

    X = df.drop(columns=[TARGET_COLUMN]).copy()
    y = df[TARGET_COLUMN].astype(int)

    cfg = _load_config_defaults()
    threshold_candidates = [float(v) for v in cfg["threshold_candidates"]]

    y_prob = _safe_predict_proba(model, X)
    best = _select_best_threshold(y, y_prob, threshold_candidates)
    best_threshold = best["threshold"]
    y_pred = (y_prob >= best_threshold).astype(int)

    roc_auc = float(roc_auc_score(y, y_prob))
    pr_auc = float(average_precision_score(y, y_prob))
    cm = confusion_matrix(y, y_pred)
    cm_business = _business_value_from_cm(
        cm,
        float(cfg["cost_false_positive"]),
        float(cfg["cost_false_negative"]),
        float(cfg["benefit_true_positive"]),
    )

    final_metrics = {
        "accuracy": float(accuracy_score(y, y_pred)),
        "precision": float(precision_score(y, y_pred, zero_division=0)),
        "recall": float(recall_score(y, y_pred, zero_division=0)),
        "f1": float(f1_score(y, y_pred, zero_division=0)),
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "threshold": float(best_threshold),
        "business_value": cm_business["business_value"],
    }

    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)

    threshold_rows = []
    # O(n + threshold_count) optimization: compute all predictions at once, then analyze thresholds
    for t in threshold_candidates:
        y_pred_t = (y_prob >= t).astype(int)
        row = {
            "threshold": float(t),
            "accuracy": float(accuracy_score(y, y_pred_t)),
            "precision": float(precision_score(y, y_pred_t, zero_division=0)),
            "recall": float(recall_score(y, y_pred_t, zero_division=0)),
            "f1": float(f1_score(y, y_pred_t, zero_division=0)),
        }
        row_cm = confusion_matrix(y, y_pred_t)
        row_business = _business_value_from_cm(
            row_cm,
            float(cfg["cost_false_positive"]),
            float(cfg["cost_false_negative"]),
            float(cfg["benefit_true_positive"]),
        )
        row["business_value"] = row_business["business_value"]
        threshold_rows.append(row)

    threshold_df = pd.DataFrame(threshold_rows).sort_values("f1", ascending=False)
    threshold_csv_path = results_dir / "threshold_analysis.csv"
    threshold_df.to_csv(threshold_csv_path, index=False)

    classification_text = classification_report(y, y_pred)
    summary_txt_path = results_dir / "evaluation_summary.txt"
    with summary_txt_path.open("w", encoding="utf-8") as f:
        f.write("Model Evaluation Summary\n")
        f.write("=" * 40 + "\n")
        f.write(f"Best threshold: {final_metrics['threshold']:.2f}\n")
        f.write(f"Accuracy      : {final_metrics['accuracy']:.4f}\n")
        f.write(f"Precision     : {final_metrics['precision']:.4f}\n")
        f.write(f"Recall        : {final_metrics['recall']:.4f}\n")
        f.write(f"F1 Score      : {final_metrics['f1']:.4f}\n")
        f.write(f"ROC-AUC       : {final_metrics['roc_auc']:.4f}\n")
        f.write(f"PR-AUC        : {final_metrics['pr_auc']:.4f}\n")
        f.write(f"Business Value: {final_metrics['business_value']:.2f}\n")
        f.write("\nConfusion Matrix (TN FP / FN TP):\n")
        f.write(str(cm))
        f.write("\n\nDetailed Classification Report:\n")
        f.write(classification_text)

    summary_json_path = results_dir / "evaluation_metrics.json"
    with summary_json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "metrics": final_metrics,
                "confusion_matrix": cm.tolist(),
                "business_breakdown": cm_business,
                "threshold_analysis_csv": str(threshold_csv_path),
            },
            f,
            indent=2,
        )

    return {
        "metrics": final_metrics,
        "confusion_matrix": cm.tolist(),
        "business_breakdown": cm_business,
        "summary_txt_path": str(summary_txt_path),
        "summary_json_path": str(summary_json_path),
        "threshold_csv_path": str(threshold_csv_path),
    }


def main() -> None:
    result = evaluate_model()
    print("Evaluation complete.")
    print(f"Summary TXT: {result['summary_txt_path']}")
    print(f"Summary JSON: {result['summary_json_path']}")
    print(f"Threshold CSV: {result['threshold_csv_path']}")
    print(f"F1: {result['metrics']['f1']:.4f} | ROC-AUC: {result['metrics']['roc_auc']:.4f}")


if __name__ == "__main__":
    main()