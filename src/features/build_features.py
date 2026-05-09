from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


BASE_FEATURE_COLUMNS = [
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
TARGET_COLUMN = "dropoff_label"


def _validate_input_schema(df: pd.DataFrame) -> None:
    required = BASE_FEATURE_COLUMNS + [TARGET_COLUMN]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns for feature engineering: {missing_cols}")


def _add_numeric_behavior_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Efficiency-oriented features: same activity can imply different retention risk
    # depending on account age and recent inactivity.
    df["activity_per_day"] = df["frequency_total"] / (df["days_signup_age"] + 1.0)
    df["recency_ratio"] = df["recency_days"] / (df["days_signup_age"] + 1.0)
    df["feature_use_ratio"] = df["feature_count_used"] / (df["frequency_total"] + 1.0)

    # Engagement depth combines session quality and product breadth.
    df["engagement_depth_score"] = df["session_duration_avg"] * df["feature_count_used"]

    # Early warning score: larger values indicate higher risk behavior trend.
    df["dropoff_risk_proxy"] = (
        0.6 * df["recency_days"]
        - 0.25 * df["frequency_total"]
        - 0.3 * df["session_duration_avg"]
        - 0.4 * df["feature_count_used"]
    )

    return df


def _add_categorical_risk_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    device_risk_map = {"mobile": 1.0, "desktop": 0.6, "tablet": 0.8}
    segment_risk_map = {"free": 1.0, "trial": 0.8, "premium": 0.3}

    df["device_risk_weight"] = df["device_type"].map(device_risk_map).fillna(0.8)
    df["segment_risk_weight"] = df["user_segment"].map(segment_risk_map).fillna(0.9)

    # Interaction between behavioral and business context.
    df["weighted_risk_proxy"] = df["dropoff_risk_proxy"] * df["segment_risk_weight"]
    return df


def _final_feature_cleanup(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c != TARGET_COLUMN]

    for col in numeric_cols:
        df[col] = np.where(np.isfinite(df[col]), df[col], 0.0)

    # Ensure target is int for classifiers when present.
    if TARGET_COLUMN in df.columns:
        df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)
    return df


def engineer_features_for_inference(base_df: pd.DataFrame) -> pd.DataFrame:
    """Apply same feature transformations used in training for API/dashboard inference."""
    df = base_df.copy()
    df = _add_numeric_behavior_features(df)
    df = _add_categorical_risk_features(df)
    df = _final_feature_cleanup(df)
    return df


def build_features(clean_data_path: str = "data/processed/clean_user_data.csv") -> pd.DataFrame:
    """Create model-ready features from cleaned user behavior data."""
    df = pd.read_csv(clean_data_path)
    _validate_input_schema(df)

    feature_df = engineer_features_for_inference(df)

    feature_df = feature_df.dropna().reset_index(drop=True)
    return feature_df


def _build_feature_report(df: pd.DataFrame) -> Dict[str, object]:
    engineered_cols: List[str] = [
        "activity_per_day",
        "recency_ratio",
        "feature_use_ratio",
        "engagement_depth_score",
        "dropoff_risk_proxy",
        "device_risk_weight",
        "segment_risk_weight",
        "weighted_risk_proxy",
    ]

    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "engineered_feature_count": len(engineered_cols),
        "engineered_features": engineered_cols,
        "target_rate": float(df[TARGET_COLUMN].mean()),
    }


def main() -> None:
    model_output_path = Path("data/processed/model_data.csv")
    full_feature_output_path = Path("data/processed/engineered_features.csv")
    report_path = Path("results/feature_engineering_report.txt")

    model_output_path.parent.mkdir(parents=True, exist_ok=True)
    full_feature_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    feature_df = build_features("data/processed/clean_user_data.csv")

    # Save full engineered table for analysis and future advanced models.
    feature_df.to_csv(full_feature_output_path, index=False)

    # Keep legacy compatibility path used by existing training script.
    feature_df.to_csv(model_output_path, index=False)

    report = _build_feature_report(feature_df)
    with report_path.open("w", encoding="utf-8") as f:
        f.write("Feature Engineering Report\n")
        f.write("=" * 35 + "\n")
        f.write(f"Rows: {report['rows']}\n")
        f.write(f"Columns: {report['columns']}\n")
        f.write(f"Engineered feature count: {report['engineered_feature_count']}\n")
        f.write(f"Target positive rate: {report['target_rate']:.4f}\n")
        f.write("Engineered features:\n")
        for col in report["engineered_features"]:
            f.write(f"- {col}\n")

    print(f"Model-ready dataset saved: {model_output_path}")
    print(f"Engineered dataset saved: {full_feature_output_path}")
    print(f"Feature report saved: {report_path}")
    print(f"Shape: {feature_df.shape}")


if __name__ == "__main__":
    main()
