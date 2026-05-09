"""
Monitoring and metrics tracking for production ML pipeline.
Tracks API latency, prediction counters, drift stubs, and periodic persistence.
"""

from __future__ import annotations

import json
import time
from collections import deque
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Deque, Dict, List, Optional

import pandas as pd


METRICS_DIR = Path("metrics")
OBS_METRICS_DIR = Path("mlops") / "observability" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)
OBS_METRICS_DIR.mkdir(parents=True, exist_ok=True)

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


@dataclass
class MetricEvent:
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    event_type: str = ""
    module: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    request_id: str = field(default_factory=lambda: request_id_var.get())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsCollector:
    """Thread-safe in-memory metrics collector with periodic export capability."""

    def __init__(self):
        self._lock = Lock()
        self.events: List[MetricEvent] = []
        self.counters: Dict[str, int] = {}
        self.latency_ms: Deque[float] = deque(maxlen=5000)
        self.recent_probabilities: Deque[float] = deque(maxlen=1000)

        self.persist_interval_seconds: int = 60
        self.persist_min_new_events: int = 25
        self._last_persist_time: float = time.time()
        self._last_persist_event_count: int = 0

    def record(
        self,
        event_type: str,
        module: str,
        metric_name: str,
        metric_value: float,
        **metadata: Any,
    ) -> None:
        event = MetricEvent(
            event_type=event_type,
            module=module,
            metric_name=metric_name,
            metric_value=float(metric_value),
            metadata=metadata,
        )
        with self._lock:
            self.events.append(event)

    def increment_counter(self, key: str, amount: int = 1) -> None:
        with self._lock:
            self.counters[key] = self.counters.get(key, 0) + amount

    def record_latency(self, latency_ms: float, endpoint: str = "unknown") -> None:
        with self._lock:
            self.latency_ms.append(float(latency_ms))
        self.record(
            event_type="latency",
            module="api",
            metric_name="request_latency_ms",
            metric_value=float(latency_ms),
            endpoint=endpoint,
        )

    def record_prediction(self, probability: float, risk_level: str) -> None:
        with self._lock:
            self.recent_probabilities.append(float(probability))
            self.counters["predictions_total"] = self.counters.get("predictions_total", 0) + 1
            risk_key = f"predictions_risk_{risk_level}"
            self.counters[risk_key] = self.counters.get(risk_key, 0) + 1

        self.record(
            event_type="prediction",
            module="api",
            metric_name="dropoff_probability",
            metric_value=float(probability),
            risk_level=risk_level,
        )

    def get_drift_stub(self, baseline_mean: float = 0.5, warn_threshold: float = 0.10) -> Dict[str, Any]:
        with self._lock:
            probs = list(self.recent_probabilities)

        if not probs:
            return {
                "status": "insufficient_data",
                "baseline_mean": baseline_mean,
                "current_mean": None,
                "distance": None,
                "samples": 0,
            }

        current_mean = float(sum(probs) / len(probs))
        distance = abs(current_mean - baseline_mean)
        status = "alert" if distance >= warn_threshold else "ok"

        return {
            "status": status,
            "baseline_mean": baseline_mean,
            "current_mean": current_mean,
            "distance": distance,
            "samples": len(probs),
            "threshold": warn_threshold,
        }

    def get_api_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            latencies = list(self.latency_ms)
            counters = dict(self.counters)
            total_events = len(self.events)

        # O(1) average calculation
        avg_latency = float(sum(latencies) / len(latencies)) if latencies else 0.0
        
        # O(n log n) p95 calculation using sort instead of pd.Series.quantile() - O(n) better for large datasets
        if len(latencies) >= 2:
            sorted_latencies = sorted(latencies)
            idx = int(0.95 * len(sorted_latencies))
            p95_latency = float(sorted_latencies[idx])
        else:
            p95_latency = avg_latency

        return {
            "events_total": total_events,
            "counters": counters,
            "latency": {
                "count": len(latencies),
                "avg_ms": avg_latency,
                "p95_ms": p95_latency,
            },
            "drift_stub": self.get_drift_stub(),
        }

    def save_metrics(self, output_path: Optional[str] = None) -> str:
        out_path: Path
        if output_path is None:
            out_path = METRICS_DIR / f"metrics_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.jsonl"
        else:
            out_path = Path(output_path)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            with self._lock:
                events = list(self.events)
            for event in events:
                f.write(json.dumps(event.to_dict(), ensure_ascii=True) + "\n")

        return str(out_path)

    def persist_snapshot(self, output_path: Optional[str] = None) -> str:
        out_path: Path
        if output_path is None:
            out_path = OBS_METRICS_DIR / f"snapshot_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        else:
            out_path = Path(output_path)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "snapshot": self.get_api_snapshot(),
            "summary": self.get_summary(),
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return str(out_path)

    def maybe_persist(self, force: bool = False) -> Dict[str, str] | None:
        with self._lock:
            current_events = len(self.events)
        new_events = current_events - self._last_persist_event_count
        elapsed = time.time() - self._last_persist_time

        should_persist = force or (
            elapsed >= self.persist_interval_seconds and new_events >= self.persist_min_new_events
        )
        if not should_persist:
            return None

        metrics_path = self.save_metrics()
        snapshot_path = self.persist_snapshot()

        self._last_persist_time = time.time()
        self._last_persist_event_count = current_events
        return {
            "metrics_path": metrics_path,
            "snapshot_path": snapshot_path,
        }

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            events = list(self.events)

        if not events:
            return {}

        df = pd.DataFrame([e.to_dict() for e in events])
        return {
            "total_events": len(events),
            "event_types": df["event_type"].value_counts().to_dict(),
            "modules": df["module"].value_counts().to_dict(),
            "duration_seconds": (
                (pd.to_datetime(df["timestamp"].max()) - pd.to_datetime(df["timestamp"].min())).total_seconds()
                if len(df) > 1
                else 0
            ),
        }


_collector = MetricsCollector()


def get_collector() -> MetricsCollector:
    return _collector


class Timer:
    def __init__(self, module: str, operation: str):
        self.module = module
        self.operation = operation
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        elapsed = time.time() - self.start_time
        collector = get_collector()
        collector.record(
            event_type="timing",
            module=self.module,
            metric_name=self.operation,
            metric_value=elapsed,
        )
