"""
Model versioning and tracking for production MLOps.
Tracks model versions, metadata, and performance over time.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


MODELS_DIR = Path("models")
REGISTRY_PATH = MODELS_DIR / "model_registry.json"


@dataclass
class ModelMetadata:
    """Metadata for a model version."""

    version: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    model_type: str = ""
    model_path: str = ""
    preprocessor_path: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    training_data_rows: int = 0
    feature_count: int = 0
    threshold: float = 0.5
    tags: Dict[str, str] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelRegistry:
    """Central registry for model versioning and tracking."""

    def __init__(self):
        self.models: List[ModelMetadata] = []
        self._load_registry()

    def _load_registry(self) -> None:
        """Load existing model registry from file."""
        if REGISTRY_PATH.exists():
            try:
                with REGISTRY_PATH.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                self.models = [ModelMetadata(**m) for m in data]
            except Exception:
                self.models = []

    def register_model(
        self,
        version: str,
        model_type: str,
        model_path: str,
        metrics: Dict[str, float],
        training_data_rows: int,
        feature_count: int,
        threshold: float = 0.5,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> ModelMetadata:
        """Register a new model version."""
        metadata = ModelMetadata(
            version=version,
            model_type=model_type,
            model_path=model_path,
            metrics=metrics,
            training_data_rows=training_data_rows,
            feature_count=feature_count,
            threshold=threshold,
            description=description,
            tags=tags or {},
        )

        self.models.append(metadata)
        self._save_registry()
        return metadata

    def get_model(self, version: str) -> Optional[ModelMetadata]:
        """Get model metadata by version."""
        for model in self.models:
            if model.version == version:
                return model
        return None

    def get_latest_model(self) -> Optional[ModelMetadata]:
        """Get the latest model by creation time."""
        if not self.models:
            return None
        return max(self.models, key=lambda m: m.created_at)

    def get_best_model(self, metric: str = "roc_auc") -> Optional[ModelMetadata]:
        """Get best model by a specific metric."""
        valid_models = [m for m in self.models if metric in m.metrics]
        if not valid_models:
            return None
        return max(valid_models, key=lambda m: m.metrics[metric])

    def list_models(self, limit: Optional[int] = None) -> List[ModelMetadata]:
        """List all registered models."""
        sorted_models = sorted(self.models, key=lambda m: m.created_at, reverse=True)
        return sorted_models[:limit] if limit else sorted_models

    def _save_registry(self) -> None:
        """Save model registry to file."""
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        with REGISTRY_PATH.open("w", encoding="utf-8") as f:
            json.dump([m.to_dict() for m in self.models], f, indent=2)

    def get_registry_summary(self) -> Dict[str, Any]:
        """Get summary of registered models."""
        return {
            "total_models": len(self.models),
            "latest_version": self.get_latest_model().version if self.get_latest_model() else None,
            "best_model_roc_auc": self.get_best_model("roc_auc").version if self.get_best_model("roc_auc") else None,
            "models": [
                {
                    "version": m.version,
                    "model_type": m.model_type,
                    "created_at": m.created_at,
                    "roc_auc": m.metrics.get("roc_auc"),
                }
                for m in self.list_models(limit=10)
            ],
        }


# Global registry instance
_registry = ModelRegistry()


def get_registry() -> ModelRegistry:
    """Get the global model registry."""
    return _registry
