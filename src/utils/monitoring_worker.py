from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from src.utils.logger import get_logger


logger = get_logger("monitoring_worker")


class BackgroundMonitorWorker:
    """Lightweight background worker for periodic monitoring cycles."""

    def __init__(
        self,
        cycle_fn: Callable[[], None],
        interval_seconds: float = 30.0,
        worker_name: str = "monitoring-worker",
    ):
        self.cycle_fn = cycle_fn
        self.interval_seconds = float(interval_seconds)
        self.worker_name = worker_name
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name=self.worker_name, daemon=True)
        self._thread.start()
        logger.info("worker_started", worker_name=self.worker_name, interval_seconds=self.interval_seconds)

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_seconds)
        logger.info("worker_stopped", worker_name=self.worker_name)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            start = time.perf_counter()
            try:
                self.cycle_fn()
            except Exception as exc:
                logger.error("worker_cycle_failed", worker_name=self.worker_name, error=str(exc))

            elapsed = time.perf_counter() - start
            wait_time = max(0.0, self.interval_seconds - elapsed)
            self._stop_event.wait(wait_time)
