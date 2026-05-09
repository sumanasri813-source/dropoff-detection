"""
Data validation and schema checking for production pipeline.
Ensures data quality and early detection of anomalies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class DataQualityReport:
    """Report on data quality checks."""

    total_rows: int = 0
    missing_values: Dict[str, int] = None
    duplicate_rows: int = 0
    data_type_errors: List[str] = None
    range_violations: List[str] = None
    passed: bool = False

    def __post_init__(self):
        if self.missing_values is None:
            self.missing_values = {}
        if self.data_type_errors is None:
            self.data_type_errors = []
        if self.range_violations is None:
            self.range_violations = []


class DataValidator:
    """Validates data against schema and business rules."""

    REQUIRED_COLUMNS = {
        "days_signup_age",
        "recency_days",
        "frequency_total",
        "session_duration_avg",
        "feature_count_used",
        "device_type",
        "os_type",
        "user_segment",
        "region",
    }

    NUMERIC_COLUMNS = {
        "days_signup_age",
        "recency_days",
        "frequency_total",
        "session_duration_avg",
        "feature_count_used",
    }

    CATEGORICAL_OPTIONS = {
        "device_type": {"mobile", "desktop", "tablet"},
        "os_type": {"windows", "mac", "android", "ios", "linux"},
        "user_segment": {"free", "trial", "premium"},
        "region": {"north", "south", "east", "west"},
    }

    VALID_RANGES = {
        "days_signup_age": (0, 1000),
        "recency_days": (0, 500),
        "frequency_total": (0, 1000),
        "session_duration_avg": (0, 300),
        "feature_count_used": (0, 100),
    }

    @classmethod
    def validate(cls, df: pd.DataFrame, target_column: Optional[str] = None) -> DataQualityReport:
        """Run comprehensive data validation. O(n) single-pass optimized version."""
        report = DataQualityReport(total_rows=len(df))
        df_columns = set(df.columns)

        # Check required columns - O(k) where k = num required columns
        missing_cols = cls.REQUIRED_COLUMNS - df_columns
        if missing_cols:
            report.data_type_errors.append(f"Missing required columns: {missing_cols}")
            return report

        # Single pass: collect all violations simultaneously - O(n)
        present_required = cls.REQUIRED_COLUMNS & df_columns
        null_counts = df[list(present_required)].isnull().sum()
        report.missing_values = null_counts[null_counts > 0].to_dict()
        report.duplicate_rows = int(df.duplicated().sum())

        # Vectorized numeric type checks - O(k)
        for col in cls.NUMERIC_COLUMNS:
            if col in df_columns and not pd.api.types.is_numeric_dtype(df[col]):
                report.data_type_errors.append(f"Column '{col}' is not numeric")

        # Vectorized categorical checks - O(n + k*u) where u=unique values
        for col, valid_set in cls.CATEGORICAL_OPTIONS.items():
            if col in df_columns:
                col_uniques = set(df[col].unique())
                invalid = col_uniques - valid_set
                if invalid:
                    report.data_type_errors.append(f"Column '{col}' has invalid values: {invalid}")

        # Vectorized range checks - O(n)
        for col, (min_val, max_val) in cls.VALID_RANGES.items():
            if col in df_columns:
                violations = ((df[col] < min_val) | (df[col] > max_val)).sum()
                if violations > 0:
                    report.range_violations.append(f"Column '{col}': {int(violations)} values out of range [{min_val}, {max_val}]")

        # Check target if provided - O(u) where u=unique values
        if target_column and target_column in df_columns:
            unique_targets = set(df[target_column].dropna().unique())
            if not unique_targets.issubset({0, 1}):
                report.data_type_errors.append(f"Target column '{target_column}' is not binary (0/1)")

        report.passed = len(report.data_type_errors) == 0 and len(report.missing_values) == 0
        return report

    @classmethod
    def report_to_dict(cls, report: DataQualityReport) -> Dict[str, Any]:
        """Convert report to dictionary for logging."""
        return {
            "total_rows": report.total_rows,
            "missing_values": report.missing_values,
            "duplicate_rows": report.duplicate_rows,
            "data_type_errors": report.data_type_errors,
            "range_violations": report.range_violations,
            "passed": report.passed,
        }
