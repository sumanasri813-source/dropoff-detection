from __future__ import annotations

import os
from functools import wraps
from typing import Callable, Tuple

from flask import jsonify, request


def load_security_config(config_path: str = "config.yaml") -> Tuple[bool, str | None]:
    required = False
    key: str | None = None

    try:
        from src.utils.config_loader import load_config

        cfg = load_config(config_path)
        security = cfg.get("security", {}) if isinstance(cfg.get("security", {}), dict) else {}
        required = bool(security.get("require_auth", False))

        env_var_name = str(security.get("api_key_env_var", "API_KEY")).strip() or "API_KEY"
        key_from_env = os.getenv(env_var_name, "").strip()
        key_from_config = str(security.get("api_key", "")).strip()
        key = key_from_env or key_from_config or None
    except Exception:
        pass

    return required, key


def create_api_key_guard(security_state_getter: Callable[[], Tuple[bool, str | None]]):
    def guard(view_fn: Callable):
        @wraps(view_fn)
        def wrapped(*args, **kwargs):
            require_auth, api_key = security_state_getter()
            if not require_auth:
                return view_fn(*args, **kwargs)

            candidate = request.headers.get("X-API-Key", "").strip()
            if api_key and candidate == api_key:
                return view_fn(*args, **kwargs)

            return jsonify({"error": "Unauthorized. Missing or invalid X-API-Key."}), 401

        return wrapped

    return guard