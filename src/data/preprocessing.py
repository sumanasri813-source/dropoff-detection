from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from src.data.data_loader import (
    CATEGORICAL_COLUMNS,
    NUMERIC_COLUMNS,
    TARGET_COLUMN,
    load_raw_data,
)


ALLOWED_DEVICE_TYPE = {"mobile", "desktop", "tablet"}
ALLOWED_OS_TYPE = {"windows", "mac", "android", "ios", "linux"}
ALLOWED_USER_SEGMENT = {"free", "trial", "premium"}
ALLOWED_REGION = {"north", "south", "east", "west"}


@dataclass(frozen=True)
class PreprocessResult:
    clean_df: pd.DataFrame
    report: Dict[str, int]


def _normalize_categories(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["device_type"] = df["device_type"].astype(str).str.strip().str.lower()
    df["os_type"] = df["os_type"].astype(str).str.strip().str.lower()
    df["user_segment"] = df["user_segment"].astype(str).str.strip().str.lower()
    df["region"] = df["region"].astype(str).str.strip().str.lower()

    df.loc[~df["device_type"].isin(ALLOWED_DEVICE_TYPE), "device_type"] = "mobile"
    df.loc[~df["os_type"].isin(ALLOWED_OS_TYPE), "os_type"] = "android"
    df.loc[~df["user_segment"].isin(ALLOWED_USER_SEGMENT), "user_segment"] = "free"
    df.loc[~df["region"].isin(ALLOWED_REGION), "region"] = "north"
    return df


def preprocess_dataframe(raw_df: pd.DataFrame) -> PreprocessResult:
    """Apply deterministic cleaning rules suitable for production batch jobs."""
    df = raw_df.copy()
    input_rows = int(df.shape[0])

    # Remove exact duplicates while preserving first occurrence.
    before_dedup = int(df.shape[0])
    df = df.drop_duplicates().reset_index(drop=True)
    duplicates_removed = before_dedup - int(df.shape[0])

    # Ensure numeric columns are numeric; invalid values become NaN.
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Coerce target to binary 0/1.
    df[TARGET_COLUMN] = pd.to_numeric(df[TARGET_COLUMN], errors="coerce").fillna(0).astype(int)
    df[TARGET_COLUMN] = np.where(df[TARGET_COLUMN] > 0, 1, 0)

    # Median imputation for robust handling of skewed behavior features.
    for col in NUMERIC_COLUMNS:
        median_val = float(df[col].median()) if df[col].notna().any() else 0.0
        df[col] = df[col].fillna(median_val)

    # Enforce non-negative constraints where required.
    bounded_cols = ["days_signup_age", "recency_days", "frequency_total", "feature_count_used"]
    for col in bounded_cols:
        df[col] = df[col].clip(lower=0)

    # Reduce extreme values without dropping records - vectorized inline O(n)
    for col in NUMERIC_COLUMNS:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            df[col] = df[col].clip(lower=lower, upper=upper)

    # Clean and map categorical values to known domain sets.
    df = _normalize_categories(df)

    # Final defensive pass to remove any remaining nulls.
    before_dropna = int(df.shape[0])
    df = df.dropna(subset=NUMERIC_COLUMNS + CATEGORICAL_COLUMNS + [TARGET_COLUMN]).reset_index(drop=True)
    rows_dropped_null = before_dropna - int(df.shape[0])

    report = {
        "input_rows": input_rows,
        "output_rows": int(df.shape[0]),
        "duplicates_removed": duplicates_removed,
        "rows_dropped_null": rows_dropped_null,
    }
    return PreprocessResult(clean_df=df, report=report)


def run_preprocessing(
    raw_csv_path: str = "data/raw/user_data.csv",
    processed_csv_path: str = "data/processed/clean_user_data.csv",
    report_path: str = "results/preprocessing_report.txt",
) -> Dict[str, int]:
    load_result = load_raw_data(raw_csv_path)
    preprocess_result = preprocess_dataframe(load_result.dataframe)

    output_path = Path(processed_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    preprocess_result.clean_df.to_csv(output_path, index=False)

    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with report_file.open("w", encoding="utf-8") as f:
        f.write("Preprocessing Report\n")
        f.write("=" * 30 + "\n")
        f.write(f"Input rows: {preprocess_result.report['input_rows']}\n")
        f.write(f"Output rows: {preprocess_result.report['output_rows']}\n")
        f.write(f"Duplicates removed: {preprocess_result.report['duplicates_removed']}\n")
        f.write(f"Rows dropped (remaining nulls): {preprocess_result.report['rows_dropped_null']}\n")

    return preprocess_result.report


def main() -> None:
    report = run_preprocessing()
    print("Preprocessing completed.")
    print(report)


if __name__ == "__main__":
    main()
