from __future__ import annotations

from typing import Tuple


def load_api_config(config_path: str = "config.yaml") -> Tuple[str, int, bool]:
    host = "0.0.0.0"
    port = 5000
    debug = False
    try:
        from src.utils.config_loader import load_config

        cfg = load_config(config_path)
        api_cfg = cfg.get("deployment", {}).get("api", {})
        host = str(api_cfg.get("host", host))
        port = int(api_cfg.get("port", port))
        debug = bool(api_cfg.get("debug", debug))
    except Exception:
        pass
    return host, port, debug


def load_model_path(config_path: str = "config.yaml") -> str:
    model_path = "models/final_model.pkl"
    try:
        from src.utils.config_loader import load_config

        cfg = load_config(config_path)
        model_path = str(cfg.get("deployment", {}).get("model_path", model_path))
    except Exception:
        pass
    return model_path


def load_monitoring_config(config_path: str = "config.yaml") -> tuple[float, int]:
    interval_sec = 30.0
    throttle_min = 5
    try:
        from src.utils.config_loader import load_config

        cfg = load_config(config_path)
        monitoring = cfg.get("monitoring", {})
        interval_sec = float(monitoring.get("monitor_worker_interval_sec", interval_sec))
        throttle_min = int(monitoring.get("alert_throttle_minutes", throttle_min))
    except Exception:
        pass
    return interval_sec, throttle_min