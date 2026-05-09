from __future__ import annotations

import time
import unittest

from src.utils.monitoring_worker import BackgroundMonitorWorker


class MonitoringWorkerTests(unittest.TestCase):
    def test_worker_runs_periodic_cycles(self) -> None:
        calls = []

        def cycle() -> None:
            calls.append(time.time())

        worker = BackgroundMonitorWorker(cycle_fn=cycle, interval_seconds=0.1, worker_name="test-worker")
        worker.start()
        time.sleep(0.35)
        worker.stop(timeout_seconds=1.0)

        self.assertGreaterEqual(len(calls), 2)
        self.assertFalse(worker.is_running())

    def test_worker_survives_cycle_exception(self) -> None:
        state = {"count": 0}

        def cycle() -> None:
            state["count"] += 1
            if state["count"] == 1:
                raise RuntimeError("first cycle fails")

        worker = BackgroundMonitorWorker(cycle_fn=cycle, interval_seconds=0.1, worker_name="test-worker-fail")
        worker.start()
        time.sleep(0.35)
        worker.stop(timeout_seconds=1.0)

        self.assertGreaterEqual(state["count"], 2)
        self.assertFalse(worker.is_running())


if __name__ == "__main__":
    unittest.main()
