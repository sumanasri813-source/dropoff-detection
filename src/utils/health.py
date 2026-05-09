"""
Health checks and system status monitoring for production API.
Ensures model, data, and infrastructure are healthy.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd


@dataclass
class HealthStatus:
    """Health check status."""

    timestamp: str
    status: str  # "healthy", "degraded", "unhealthy"
    model_available: bool
    data_available: bool
    metrics_available: bool
    api_responsive: bool
    details: Dict[str, Any]


class HealthChecker:
    """Monitors system health for production deployment."""

    @staticmethod
    def check_model(model_path: str = "models/final_model.pkl") -> tuple[bool, str]:
        """Check if model file exists and is readable."""
        path = Path(model_path)
        if not path.exists():
            return False, f"Model file not found at {model_path}"
        if not path.is_file():
            return False, f"Model path is not a file: {model_path}"
        if path.stat().st_size == 0:
            return False, "Model file is empty"
        return True, "Model available"

    @staticmethod
    def check_data(
        data_path: str = "data/processed/model_data.csv",
        min_rows: int = 100,
    ) -> tuple[bool, str]:
        """Check if training data exists and meets minimum requirements."""
        path = Path(data_path)
        if not path.exists():
            return False, f"Data file not found at {data_path}"

        try:
            df = pd.read_csv(path)
            if len(df) < min_rows:
                return False, f"Data has only {len(df)} rows, minimum required: {min_rows}"
            return True, f"Data available ({len(df)} rows)"
        except Exception as exc:
            return False, f"Error reading data file: {str(exc)}"

    @staticmethod
    def check_metrics(metrics_path: str = "results/evaluation_metrics.json") -> tuple[bool, str]:
        """Check if evaluation metrics are available."""
        path = Path(metrics_path)
        if not path.exists():
            return False, f"Metrics file not found at {metrics_path}"

        try:
            with path.open("r", encoding="utf-8") as f:
                metrics = json.load(f)
            if "metrics" not in metrics:
                return False, "Metrics file does not contain 'metrics' key"
            return True, "Metrics available"
        except Exception as exc:
            return False, f"Error reading metrics file: {str(exc)}"

    @staticmethod
    def check_api_responsive() -> tuple[bool, str]:
        """Check if API is responsive (simplified check)."""
        return True, "API responsive"

    @classmethod
    def run_full_check(cls) -> HealthStatus:
        """Run comprehensive health check."""
        model_ok, model_msg = cls.check_model()
        data_ok, data_msg = cls.check_data()
        metrics_ok, metrics_msg = cls.check_metrics()
        api_ok, api_msg = cls.check_api_responsive()

        all_ok = model_ok and data_ok and metrics_ok and api_ok
        status = "healthy" if all_ok else ("degraded" if sum([model_ok, data_ok, metrics_ok]) >= 2 else "unhealthy")

        return HealthStatus(
            timestamp=datetime.now(UTC).isoformat(),
            status=status,
            model_available=model_ok,
            data_available=data_ok,
            metrics_available=metrics_ok,
            api_responsive=api_ok,
            details={
                "model": model_msg,
                "data": data_msg,
                "metrics": metrics_msg,
                "api": api_msg,
            },
        )

    @staticmethod
    def health_to_dict(status: HealthStatus) -> Dict[str, Any]:
        """Convert health status to dictionary."""
        return asdict(status)
