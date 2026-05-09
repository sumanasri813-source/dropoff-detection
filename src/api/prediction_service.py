from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, cast

import joblib
import pandas as pd

from src.features.build_features import engineer_features_for_inference
from src.utils.logger import get_logger
from src.utils.metrics import get_collector

FEATURE_KEYS: List[str] = [
    "days_signup_age",
    "recency_days",
    "frequency_total",
    "session_duration_avg",
    "feature_count_used",
    "device_type",
    "os_type",
    "user_segment",
    "region",
]

DEFAULT_THRESHOLD = 0.5
DEFAULT_RISK_LEVELS = {
    "high": 0.70,
    "medium": 0.40,
    "low": 0.0,
}

logger = get_logger("prediction_service")
collector = get_collector()


def _try_load_config() -> Dict[str, Any]:
    try:
        from src.utils.config_loader import load_config

        return load_config("config.yaml")
    except Exception:
        return {}


def load_decision_threshold() -> float:
    """Load threshold from evaluation output first, then config, then default."""
    eval_json = Path("results/evaluation_metrics.json")
    if eval_json.exists():
        try:
            payload = json.loads(eval_json.read_text(encoding="utf-8"))
            threshold = payload.get("metrics", {}).get("threshold")
            if threshold is not None:
                return float(threshold)
        except Exception:
            pass

    config = _try_load_config()
    threshold = config.get("prediction", {}).get("threshold", DEFAULT_THRESHOLD)
    return float(threshold)


def load_risk_levels() -> Dict[str, float]:
    config = _try_load_config()
    levels = config.get("prediction", {}).get("risk_levels", {})
    merged = DEFAULT_RISK_LEVELS.copy()
    for key in ["high", "medium", "low"]:
        if key in levels:
            merged[key] = float(levels[key])
    return merged


def get_risk_level(probability: float, risk_levels: Dict[str, float]) -> str:
    if probability >= risk_levels["high"]:
        return "high"
    if probability >= risk_levels["medium"]:
        return "medium"
    return "low"


def validate_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
    missing = [key for key in FEATURE_KEYS if key not in payload]
    if missing:
        return False, f"Missing fields: {missing}"

    numeric_keys = [
        "days_signup_age",
        "recency_days",
        "frequency_total",
        "session_duration_avg",
        "feature_count_used",
    ]
    for key in numeric_keys:
        try:
            float(payload[key])
        except (TypeError, ValueError):
            return False, f"Field '{key}' must be numeric."

    for key in ["device_type", "os_type", "user_segment", "region"]:
        if not isinstance(payload[key], str):
            return False, f"Field '{key}' must be a string."

    return True, "ok"


def payload_to_dataframe(payload: Dict[str, Any]) -> pd.DataFrame:
    normalized = {
        "user_id": float(payload.get("user_id", 0)),
        "days_signup_age": float(payload["days_signup_age"]),
        "recency_days": float(payload["recency_days"]),
        "frequency_total": float(payload["frequency_total"]),
        "session_duration_avg": float(payload["session_duration_avg"]),
        "feature_count_used": float(payload["feature_count_used"]),
        "device_type": str(payload["device_type"]).strip().lower(),
        "os_type": str(payload["os_type"]).strip().lower(),
        "user_segment": str(payload["user_segment"]).strip().lower(),
        "region": str(payload["region"]).strip().lower(),
    }
    base_columns = ["user_id"] + FEATURE_KEYS
    return pd.DataFrame([normalized], columns=base_columns)


def _align_features_to_model(model: Any, df: pd.DataFrame) -> pd.DataFrame:
    """Align features to model expectations. O(n) optimized using set operations."""
    expected_cols_raw = getattr(model, "feature_names_in_", [])
    if not len(expected_cols_raw):
        return df

    expected_cols = [str(c) for c in expected_cols_raw]
    expected_set = set(expected_cols)
    df_cols_set = set(df.columns)
    
    # Set difference for missing columns - O(k) instead of O(n*k) individual checks
    missing_cols = expected_set - df_cols_set
    aligned = df.copy()
    if missing_cols:
        for col in missing_cols:
            aligned[col] = 0.0
    
    return cast(pd.DataFrame, aligned.loc[:, expected_cols])


def predict_one(
    model: Any,
    payload: Dict[str, Any],
    threshold: float,
    risk_levels: Dict[str, float],
) -> Dict[str, Any]:
    df = payload_to_dataframe(payload)
    df = engineer_features_for_inference(df)
    df = _align_features_to_model(model, df)
    probability = float(model.predict_proba(df)[:, 1][0])
    prediction = int(probability >= threshold)
    risk_level = get_risk_level(probability, risk_levels)

    collector.record_prediction(probability=probability, risk_level=risk_level)
    logger.info(
        "prediction_scored",
        probability=round(probability, 6),
        threshold=threshold,
        risk_level=risk_level,
        predicted_label=prediction,
    )

    return {
        "dropoff_probability": round(probability, 4),
        "predicted_label": prediction,
        "risk_level": risk_level,
        "threshold_used": round(threshold, 4),
    }


def predict_batch(
    model: Any,
    records: List[Dict[str, Any]],
    threshold: float,
    risk_levels: Dict[str, float],
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for idx, payload in enumerate(records):
        ok, message = validate_payload(payload)
        if not ok:
            errors.append({"index": idx, "error": message})
            collector.increment_counter("prediction_batch_validation_errors")
            continue

        try:
            prediction = predict_one(model, payload, threshold, risk_levels)
            prediction["index"] = idx
            results.append(prediction)
        except Exception as exc:
            errors.append({"index": idx, "error": str(exc)})
            collector.increment_counter("prediction_batch_runtime_errors")

    logger.info(
        "batch_prediction_completed",
        total_records=len(records),
        successful_predictions=len(results),
        failed_predictions=len(errors),
    )

    return {
        "total_records": len(records),
        "successful_predictions": len(results),
        "failed_predictions": len(errors),
        "predictions": results,
        "errors": errors,
    }


def load_model(model_path: str = "models/final_model.pkl") -> Any:
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = joblib.load(path)
    logger.info("model_loaded", model_path=model_path)
    return model
