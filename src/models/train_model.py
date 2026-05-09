from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET_COLUMN = "dropoff_label"

try:
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
except Exception:
    logger = None


def _load_random_seed(default_seed: int = 42) -> int:
    """Read random seed from config when available; fallback to default safely."""
    try:
        from src.utils.config_loader import load_config

        config = load_config("config.yaml")
        return int(config.get("data", {}).get("random_seed", default_seed))
    except Exception:
        return default_seed


def _infer_feature_types(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    """Infer numeric vs categorical features. O(k) where k=number of columns."""
    feature_df = df.drop(columns=[TARGET_COLUMN]).copy()
    numeric_features = feature_df.select_dtypes(include=["number"]).columns.tolist()
    categorical_features = [c for c in feature_df.columns if c not in numeric_features]
    return numeric_features, categorical_features


def _build_preprocessor(numeric_features: List[str], categorical_features: List[str]) -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_features),
            ("cat", categorical_pipeline, categorical_features),
        ]
    )


def _get_model_candidates(random_seed: int) -> Dict[str, object]:
    models: Dict[str, object] = {
        "logistic_regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=12,
            min_samples_leaf=2,
            random_state=random_seed,
            class_weight="balanced_subsample",
            n_jobs=-1,
        ),
    }

    try:
        from xgboost import XGBClassifier

        models["xgboost"] = XGBClassifier(
            n_estimators=350,
            max_depth=6,
            learning_rate=0.07,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=random_seed,
        )
    except Exception:
        # Optional dependency: training still proceeds with baseline models.
        pass

    return models


def _evaluate_pipeline(pipeline: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]
    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
    }


def train_model(data_path: str = "data/processed/model_data.csv") -> Dict[str, object]:
    """Train multiple model candidates and persist the best. O(m*n*f) where m=models, n=samples, f=features."""
    random_seed = _load_random_seed()
    
    if logger:
        logger.info("Starting model training", data_path=data_path, seed=random_seed)
    
    df = pd.read_csv(data_path)
    
    if logger:
        logger.info("Data loaded", rows=len(df), columns=len(df.columns))

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' not found in {data_path}")

    X = df.drop(columns=[TARGET_COLUMN]).copy()
    y = df[TARGET_COLUMN].astype(int)

    numeric_features, categorical_features = _infer_feature_types(df)
    preprocessor = _build_preprocessor(numeric_features, categorical_features)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=random_seed,
        stratify=y,
    )

    candidates = _get_model_candidates(random_seed)
    if not candidates:
        raise RuntimeError("No model candidates available for training.")

    models_dir = Path("models")
    results_dir = Path("results")
    models_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    metrics_rows: List[Dict[str, float]] = []
    reports: Dict[str, str] = {}
    trained_paths: Dict[str, str] = {}

    best_model_name = ""
    best_model_pipeline = None
    best_roc_auc = -1.0

    for model_name, estimator in candidates.items():
        pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("classifier", estimator),
            ]
        )
        pipeline.fit(X_train, y_train)

        metrics = _evaluate_pipeline(pipeline, X_test, y_test)
        metrics["model"] = model_name
        metrics_rows.append(metrics)

        y_pred = pipeline.predict(X_test)
        reports[model_name] = classification_report(y_test, y_pred)

        model_path = models_dir / f"{model_name}.pkl"
        joblib.dump(pipeline, model_path)
        trained_paths[model_name] = str(model_path)

        if metrics["roc_auc"] > best_roc_auc:
            best_roc_auc = metrics["roc_auc"]
            best_model_name = model_name
            best_model_pipeline = pipeline

    if best_model_pipeline is None:
        raise RuntimeError("Best model selection failed.")

    # Persist best model under standard names used by downstream API/evaluation scripts.
    best_model_path = models_dir / "best_model.pkl"
    final_model_path = models_dir / "final_model.pkl"
    joblib.dump(best_model_pipeline, best_model_path)
    joblib.dump(best_model_pipeline, final_model_path)

    comparison_df = pd.DataFrame(metrics_rows).sort_values("roc_auc", ascending=False).reset_index(drop=True)
    comparison_path = results_dir / "model_comparison.csv"
    comparison_df.to_csv(comparison_path, index=False)

    detailed_report_path = results_dir / "model_metrics.txt"
    with detailed_report_path.open("w", encoding="utf-8") as f:
        f.write("Model Training Summary\n")
        f.write("=" * 45 + "\n")
        f.write(f"Best model: {best_model_name}\n")
        f.write(f"Best ROC-AUC: {best_roc_auc:.4f}\n\n")
        for model_name in comparison_df["model"].tolist():
            f.write(f"{model_name}\n")
            f.write("-" * 30 + "\n")
            row = comparison_df.loc[comparison_df["model"] == model_name].iloc[0]
            f.write(f"ROC-AUC : {row['roc_auc']:.4f}\n")
            f.write(f"Precision: {row['precision']:.4f}\n")
            f.write(f"Recall   : {row['recall']:.4f}\n")
            f.write(f"F1       : {row['f1']:.4f}\n\n")
            f.write(reports[model_name])
            f.write("\n\n")

    summary_path = results_dir / "training_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "best_model": best_model_name,
                "best_roc_auc": best_roc_auc,
                "trained_model_paths": trained_paths,
                "best_model_path": str(best_model_path),
                "final_model_path": str(final_model_path),
                "comparison_path": str(comparison_path),
            },
            f,
            indent=2,
        )

    return {
        "best_model": best_model_name,
        "best_roc_auc": float(best_roc_auc),
        "best_model_path": str(best_model_path),
        "final_model_path": str(final_model_path),
        "comparison_path": str(comparison_path),
        "metrics_path": str(detailed_report_path),
        "summary_path": str(summary_path),
    }


def main() -> None:
    results = train_model("data/processed/model_data.csv")
    
    if logger:
        logger.info("Training pipeline completed", best_model=results["best_model"], best_roc_auc=results["best_roc_auc"])
    
    print(f"Best model: {results['best_model']}")
    print(f"Best ROC-AUC: {results['best_roc_auc']:.4f}")
    print(f"Best model path: {results['best_model_path']}")
    print(f"Comparison CSV: {results['comparison_path']}")
    print(f"Detailed metrics: {results['metrics_path']}")


if __name__ == "__main__":
    main()
