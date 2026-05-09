from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}

    if not isinstance(payload, dict):
        raise ValueError(f"Config file must contain a YAML object at top level: {path}")
    return payload


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _infer_runtime_environment() -> str:
    explicit = os.getenv("APP_ENV", "").strip().lower()
    if explicit in {"dev", "staging", "prod"}:
        return explicit

    ref_name = os.getenv("GITHUB_REF_NAME", "").strip().lower()
    if ref_name == "main":
        return "prod"
    if ref_name in {"develop", "staging"}:
        return "staging"
    if ref_name:
        return "dev"

    full_ref = os.getenv("GITHUB_REF", "").strip().lower()
    if full_ref.endswith("/main"):
        return "prod"
    if full_ref.endswith("/develop") or full_ref.endswith("/staging"):
        return "staging"

    return "dev"


def _environment_config_path(environment: str) -> Path:
    return Path("mlops") / "configs" / "environments" / f"{environment}.yaml"


def _apply_compatibility_mappings(config: Dict[str, Any]) -> Dict[str, Any]:
    app_cfg = config.get("app", {}) if isinstance(config.get("app", {}), dict) else {}
    deployment_cfg = config.get("deployment", {}) if isinstance(config.get("deployment", {}), dict) else {}
    api_cfg = deployment_cfg.get("api", {}) if isinstance(deployment_cfg.get("api", {}), dict) else {}

    if app_cfg:
        api_cfg.setdefault("host", app_cfg.get("api_host", "0.0.0.0"))
        api_cfg.setdefault("port", app_cfg.get("api_port", 5000))
        api_cfg.setdefault("debug", app_cfg.get("debug", False))

        deployment_cfg["api"] = api_cfg
        config["deployment"] = deployment_cfg

    monitoring_cfg = config.get("monitoring", {}) if isinstance(config.get("monitoring", {}), dict) else {}
    if monitoring_cfg.get("log_level"):
        logging_cfg = config.get("logging", {}) if isinstance(config.get("logging", {}), dict) else {}
        logging_cfg["level"] = monitoring_cfg["log_level"]
        config["logging"] = logging_cfg

    return config


def get_runtime_environment() -> str:
    """Return runtime environment: dev, staging, or prod."""
    return _infer_runtime_environment()


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load base config and merge runtime environment config automatically."""
    base_path = Path(config_path)
    if not base_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    base_config = _load_yaml(base_path)

    runtime_env = _infer_runtime_environment()
    env_path = _environment_config_path(runtime_env)
    env_config = _load_yaml(env_path)

    merged = _deep_merge(base_config, env_config)
    merged = _apply_compatibility_mappings(merged)

    runtime_block = merged.get("runtime", {}) if isinstance(merged.get("runtime", {}), dict) else {}
    runtime_block["environment"] = runtime_env
    runtime_block["environment_config_path"] = str(env_path)
    runtime_block["environment_config_loaded"] = env_path.exists()
    merged["runtime"] = runtime_block

    return merged
