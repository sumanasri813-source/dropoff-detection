"""
Enhanced logging configuration for production deployment.
Configures structured JSON logging, log rotation, and audit trails.
"""

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class StructuredLogger:
    """Structured logging for API predictions and system events."""

    def __init__(self, name: str, log_dir: str = "logs", level=logging.INFO):
        """Initialize structured logger with rotation."""
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Main logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Prevent duplicate handlers
        if self.logger.handlers:
            self.logger.handlers.clear()

        # File handler with rotation
        log_file = self.log_dir / f"{name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )  # 10MB per file, keep 5
        file_handler.setLevel(logging.INFO)

        # JSON formatter
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler (for development)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def info(self, message: str, **kwargs):
        """Log info with structured data."""
        self._log_structured(logging.INFO, message, kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning with structured data."""
        self._log_structured(logging.WARNING, message, kwargs)

    def error(self, message: str, **kwargs):
        """Log error with structured data."""
        self._log_structured(logging.ERROR, message, kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug with structured data."""
        self._log_structured(logging.DEBUG, message, kwargs)

    def _log_structured(self, level: int, message: str, data: Dict[str, Any]):
        """Internal method to log structured data."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "data": data,
        }
        self.logger.log(level, json.dumps(log_entry))

    def log_prediction(
        self,
        user_id: Optional[int],
        prediction: int,
        probability: float,
        risk_level: str,
        request_id: str,
        latency_ms: float,
    ):
        """Log prediction event with full context."""
        self.info(
            "prediction_made",
            user_id=user_id,
            prediction=prediction,
            probability=round(probability, 4),
            risk_level=risk_level,
            request_id=request_id,
            latency_ms=round(latency_ms, 2),
        )

    def log_validation_error(self, request_id: str, error: str, payload: Dict):
        """Log validation errors."""
        self.warning(
            "validation_error",
            request_id=request_id,
            error=error,
            payload_keys=list(payload.keys()),
        )

    def log_api_error(self, request_id: str, endpoint: str, error: str, status_code: int):
        """Log API errors."""
        self.error(
            "api_error",
            request_id=request_id,
            endpoint=endpoint,
            error=error,
            status_code=status_code,
        )


class PredictionAuditLog:
    """Audit log for all predictions (for compliance/debugging)."""

    def __init__(self, log_dir: str = "logs"):
        """Initialize audit log."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.log_dir / "audit.jsonl"

    def log_prediction(
        self,
        user_id: Optional[int],
        input_features: Dict[str, Any],
        prediction: int,
        probability: float,
        risk_level: str,
        request_id: str,
    ):
        """Log prediction to audit trail (JSONL format)."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "user_id": user_id,
            "input_features": input_features,
            "prediction": prediction,
            "probability": round(probability, 4),
            "risk_level": risk_level,
        }

        with open(self.audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(audit_entry) + "\n")

    def get_recent_predictions(self, limit: int = 100) -> list:
        """Get recent predictions from audit log."""
        if not self.audit_file.exists():
            return []

        predictions = []
        with open(self.audit_file, "r", encoding="utf-8") as f:
            for line in f.readlines()[-limit:]:
                try:
                    predictions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return predictions


def get_structured_logger(name: str) -> StructuredLogger:
    """Factory function for getting structured logger."""
    return StructuredLogger(name)


def get_audit_log() -> PredictionAuditLog:
    """Factory function for getting audit log."""
    return PredictionAuditLog()
