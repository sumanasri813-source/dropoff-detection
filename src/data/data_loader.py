from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd


REQUIRED_COLUMNS = {
    "user_id",
    "days_signup_age",
    "recency_days",
    "frequency_total",
    "session_duration_avg",
    "feature_count_used",
    "device_type",
    "os_type",
    "user_segment",
    "region",
    "dropoff_label",
}

CATEGORICAL_COLUMNS = ["device_type", "os_type", "user_segment", "region"]
NUMERIC_COLUMNS = [
    "days_signup_age",
    "recency_days",
    "frequency_total",
    "session_duration_avg",
    "feature_count_used",
]
TARGET_COLUMN = "dropoff_label"


@dataclass(frozen=True)
class DataLoadResult:
    dataframe: pd.DataFrame
    metadata: Dict[str, int]


def _assert_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    """Validate required columns exist. O(k) where k=number of required columns."""
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def load_raw_data(csv_path: str) -> DataLoadResult:
    """Load raw csv and perform schema-level validation only."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Raw data file not found: {csv_path}")

    df = pd.read_csv(path)
    _assert_columns(df, REQUIRED_COLUMNS)

    metadata = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
    }
    return DataLoadResult(dataframe=df, metadata=metadata)
