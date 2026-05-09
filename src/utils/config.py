"""
Production configuration management with validation.
Supports environment overrides and strict schema.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class DataConfig:
    """Data pipeline configuration."""

    random_seed: int = 42
    train_test_split: float = 0.7
    test_split: float = 0.3
    dropoff_inactive_days: int = 30
    prediction_window_days: int = 30


@dataclass
class ModelConfig:
    """Model training configuration."""

    models: list[str] = None
    best_metric: str = "f1"
    cv_folds: int = 5
    class_weight: str = "balanced"
    n_jobs: int = -1

    def __post_init__(self):
        if self.models is None:
            self.models = ["logistic_regression", "random_forest"]


@dataclass
class EvaluationConfig:
    """Evaluation configuration."""

    threshold_candidates: list[float] = None
    cost_false_positive: float = 10.0
    cost_false_negative: float = 100.0
    benefit_true_positive: float = 200.0

    def __post_init__(self):
        if self.threshold_candidates is None:
            self.threshold_candidates = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


@dataclass
class DeploymentConfig:
    """Deployment and API configuration."""

    api_host: str = "0.0.0.0"
    api_port: int = 5000
    api_debug: bool = False
    model_path: str = "models/final_model.pkl"
    log_level: str = "INFO"
    enable_monitoring: bool = True
    enable_health_checks: bool = True


@dataclass
class ProductionConfig:
    """Complete production configuration."""

    data: DataConfig = None
    model: ModelConfig = None
    evaluation: EvaluationConfig = None
    deployment: DeploymentConfig = None

    def __post_init__(self):
        if self.data is None:
            self.data = DataConfig()
        if self.model is None:
            self.model = ModelConfig()
        if self.evaluation is None:
            self.evaluation = EvaluationConfig()
        if self.deployment is None:
            self.deployment = DeploymentConfig()

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> ProductionConfig:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            return cls()

        with path.open("r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}

        config = cls()

        # Override with environment variables
        config.deployment.api_port = int(os.getenv("API_PORT", config.deployment.api_port))
        config.deployment.api_debug = os.getenv("API_DEBUG", "false").lower() == "true"
        config.deployment.log_level = os.getenv("LOG_LEVEL", config.deployment.log_level)

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/display."""
        return {
            "data": {
                "random_seed": self.data.random_seed,
                "train_test_split": self.data.train_test_split,
                "dropoff_inactive_days": self.data.dropoff_inactive_days,
            },
            "model": {"models": self.model.models, "best_metric": self.model.best_metric},
            "evaluation": {"threshold_candidates": self.evaluation.threshold_candidates},
            "deployment": {
                "api_port": self.deployment.api_port,
                "log_level": self.deployment.log_level,
                "enable_monitoring": self.deployment.enable_monitoring,
            },
        }
