from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.utils import alerts


class AlertRulesTests(unittest.TestCase):
    def test_latency_and_health_alerts_trigger(self) -> None:
        snapshot = {
            "latency": {"p95_ms": 450.0},
            "drift_stub": {"status": "ok", "distance": 0.01, "threshold": 0.1},
        }
        rules = alerts.evaluate_alert_rules(snapshot=snapshot, health_status="degraded")

        alert_types = {item["type"] for item in rules}
        self.assertIn("service_latency", alert_types)
        self.assertIn("health_status", alert_types)

    def test_drift_alert_triggers(self) -> None:
        snapshot = {
            "latency": {"p95_ms": 10.0},
            "drift_stub": {"status": "alert", "distance": 0.25, "threshold": 0.1},
        }
        rules = alerts.evaluate_alert_rules(snapshot=snapshot, health_status="healthy")

        alert_types = {item["type"] for item in rules}
        self.assertIn("drift_stub", alert_types)

    def test_persist_alerts_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = alerts.ALERTS_PATH
            try:
                alerts.ALERTS_PATH = Path(tmpdir) / "alerts.jsonl"
                out = alerts.persist_alerts(
                    [
                        {
                            "type": "service_latency",
                            "severity": "warning",
                            "message": "test",
                            "metric": "latency.p95_ms",
                            "value": 999,
                            "threshold": 300,
                        }
                    ],
                    throttle_minutes=5
                )
                self.assertIsNotNone(out)
                out_path = Path(str(out))
                self.assertTrue(out_path.exists())
                lines = out_path.read_text(encoding="utf-8").strip().splitlines()
                self.assertGreaterEqual(len(lines), 1)
                payload = json.loads(lines[-1])
                self.assertEqual(payload["type"], "service_latency")
            finally:
                alerts.ALERTS_PATH = original_path

    def test_alert_dedup_prevents_duplicate_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = alerts.ALERTS_PATH
            alerts._last_persisted_alert.clear()
            try:
                alerts.ALERTS_PATH = Path(tmpdir) / "alerts.jsonl"
                alert_obj = {
                    "type": "service_latency",
                    "severity": "warning",
                    "message": "test",
                    "metric": "latency.p95_ms",
                    "value": 999,
                    "threshold": 300,
                }
                
                # First call should persist
                out1 = alerts.persist_alerts([alert_obj], throttle_minutes=60)
                self.assertIsNotNone(out1)
                
                # Second call with same alert and throttle_minutes=60 should NOT persist
                out2 = alerts.persist_alerts([alert_obj], throttle_minutes=60)
                self.assertIsNone(out2, "Duplicate alert within throttle window should not persist")
                
                # Verify file has exactly 1 line (only first alert persisted)
                out_path = Path(str(out1))
                lines = out_path.read_text(encoding="utf-8").strip().splitlines()
                self.assertEqual(len(lines), 1)
            finally:
                alerts.ALERTS_PATH = original_path
                alerts._last_persisted_alert.clear()


if __name__ == "__main__":
    unittest.main()
