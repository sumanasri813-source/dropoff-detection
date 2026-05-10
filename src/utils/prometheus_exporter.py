"""
Prometheus Metrics Exporter

Converts internal MetricsCollector data into Prometheus exposition format.
This allows Prometheus to scrape metrics from the /metrics endpoint.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List


def _sanitize_metric_name(name: str) -> str:
    """Convert metric name to Prometheus-compatible format (lowercase, underscores only)."""
    return name.replace("-", "_").replace(".", "_").replace("/", "_").lower()


def generate_prometheus_metrics(snapshot: Dict[str, Any]) -> str:
    """
    Convert the API metrics snapshot into Prometheus exposition format.
    
    Args:
        snapshot: Dictionary from collector.get_api_snapshot()
    
    Returns:
        String in Prometheus text exposition format
    """
    lines: List[str] = []
    
    # ── Counters ──────────────────────────────────────────────────────
    counters = snapshot.get("counters", {})
    
    # Total API requests
    total = counters.get("api_requests_total", 0)
    lines.append("# HELP dropoff_api_requests_total Total number of API requests received.")
    lines.append("# TYPE dropoff_api_requests_total counter")
    lines.append(f"dropoff_api_requests_total {total}")
    
    # Requests by status code group
    for key, value in counters.items():
        if key.startswith("api_status_"):
            group = key.replace("api_status_", "")
            lines.append(f'dropoff_api_responses_total{{status_group="{group}"}} {value}')
    
    # Requests by method and path
    for key, value in counters.items():
        if key.startswith("api_requests_") and key != "api_requests_total":
            parts = key.replace("api_requests_", "").split("_", 1)
            if len(parts) == 2:
                method, path = parts
                safe_path = _sanitize_metric_name(path)
                lines.append(f'dropoff_api_endpoint_requests_total{{method="{method}",path="{safe_path}"}} {value}')
    
    # Prediction counters
    pred_total = counters.get("predictions_total", 0)
    lines.append("# HELP dropoff_predictions_total Total predictions served.")
    lines.append("# TYPE dropoff_predictions_total counter")
    lines.append(f"dropoff_predictions_total {pred_total}")
    
    # Validation errors
    val_errors = counters.get("prediction_validation_errors", 0)
    lines.append("# HELP dropoff_prediction_validation_errors_total Validation errors on /predict.")
    lines.append("# TYPE dropoff_prediction_validation_errors_total counter")
    lines.append(f"dropoff_prediction_validation_errors_total {val_errors}")
    
    # Rate limited requests
    rate_limited = counters.get("api_rate_limited", 0)
    lines.append("# HELP dropoff_rate_limited_total Requests rejected by rate limiter.")
    lines.append("# TYPE dropoff_rate_limited_total counter")
    lines.append(f"dropoff_rate_limited_total {rate_limited}")
    
    # ── Latency ───────────────────────────────────────────────────────
    latency = snapshot.get("latency", {})
    
    lines.append("# HELP dropoff_request_latency_avg_ms Average request latency in milliseconds.")
    lines.append("# TYPE dropoff_request_latency_avg_ms gauge")
    lines.append(f'dropoff_request_latency_avg_ms {latency.get("avg_ms", 0):.4f}')
    
    lines.append("# HELP dropoff_request_latency_p95_ms 95th percentile request latency in ms.")
    lines.append("# TYPE dropoff_request_latency_p95_ms gauge")
    lines.append(f'dropoff_request_latency_p95_ms {latency.get("p95_ms", 0):.4f}')
    
    lines.append("# HELP dropoff_request_latency_count Total latency samples recorded.")
    lines.append("# TYPE dropoff_request_latency_count counter")
    lines.append(f'dropoff_request_latency_count {latency.get("count", 0)}')
    
    # ── Drift Detection ───────────────────────────────────────────────
    drift = snapshot.get("drift_stub", {})
    
    drift_status_val = 1 if drift.get("status") == "ok" else 0
    lines.append("# HELP dropoff_drift_status Model drift status (1=ok, 0=alert/insufficient).")
    lines.append("# TYPE dropoff_drift_status gauge")
    lines.append(f"dropoff_drift_status {drift_status_val}")
    
    drift_samples = drift.get("samples", 0)
    lines.append("# HELP dropoff_drift_samples Number of drift detection samples collected.")
    lines.append("# TYPE dropoff_drift_samples gauge")
    lines.append(f"dropoff_drift_samples {drift_samples}")
    
    if drift.get("distance") is not None:
        lines.append("# HELP dropoff_drift_distance Statistical distance from baseline.")
        lines.append("# TYPE dropoff_drift_distance gauge")
        lines.append(f'dropoff_drift_distance {drift.get("distance", 0):.6f}')
    
    # ── Events ────────────────────────────────────────────────────────
    events_total = snapshot.get("events_total", 0)
    lines.append("# HELP dropoff_events_total Total monitoring events recorded.")
    lines.append("# TYPE dropoff_events_total counter")
    lines.append(f"dropoff_events_total {events_total}")
    
    # ── Uptime ────────────────────────────────────────────────────────
    lines.append("# HELP dropoff_scrape_timestamp_seconds Unix timestamp of last scrape.")
    lines.append("# TYPE dropoff_scrape_timestamp_seconds gauge")
    lines.append(f"dropoff_scrape_timestamp_seconds {time.time():.0f}")
    
    return "\n".join(lines) + "\n"
