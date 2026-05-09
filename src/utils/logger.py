"""
Centralized logging module for production MLOps pipeline.
Supports structured logging, log rotation, and JSON/plain formatting without extra dependencies.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG


class _JsonFormatter(logging.Formatter):
    """Minimal JSON formatter that avoids external dependencies."""

    _skip_fields = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload["context"] = context

        extras: Dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in self._skip_fields and key not in {"context"}:
                extras[key] = value
        if extras:
            payload["extra"] = extras

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


class StructuredLogger:
    """Production-grade logger with rotating JSON file and console output."""

    def __init__(self, name: str, log_level: int = INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        if self.logger.handlers:
            return

        file_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / f"{name}.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(_JsonFormatter())
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(console_handler)

    def log(self, level: int, message: str, **extra: Any) -> None:
        self.logger.log(level, message, extra={"context": extra} if extra else None)

    def info(self, message: str, **extra: Any) -> None:
        self.log(INFO, message, **extra)

    def warning(self, message: str, **extra: Any) -> None:
        self.log(WARNING, message, **extra)

    def error(self, message: str, **extra: Any) -> None:
        self.log(ERROR, message, **extra)

    def debug(self, message: str, **extra: Any) -> None:
        self.log(DEBUG, message, **extra)

    def critical(self, message: str, **extra: Any) -> None:
        self.log(CRITICAL, message, **extra)


def get_logger(name: str, log_level: int = INFO) -> StructuredLogger:
    return StructuredLogger(name, log_level)
