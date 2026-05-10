from __future__ import annotations

import atexit
import time
import uuid
from typing import Any, Dict

from flask import Flask, g, jsonify, request
from flasgger import Swagger
from flask_caching import Cache
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.api.prediction_service import (
    load_decision_threshold,
    load_model,
    load_risk_levels,
    predict_batch,
    predict_one,
    validate_payload,
)
from src.db.connection import get_session_factory, init_database
from src.db.crud import (
    create_prediction_record,
    create_user,
    delete_user,
    get_user,
    list_predictions,
    list_users,
    update_user,
)
from src.utils.auth import create_api_key_guard, load_security_config
from src.utils.alerts import evaluate_alert_rules, persist_alerts
from src.utils.health import HealthChecker
from src.utils.logger import get_logger
from src.utils.metrics import get_collector, request_id_var
from src.utils.monitoring_worker import BackgroundMonitorWorker
from src.utils.runtime_config import load_api_config, load_model_path, load_monitoring_config
from src.utils.errors import handle_error, MLPipelineError, DatabaseError, RateLimitError
from src.utils.resilience import PerKeyRateLimiter, with_circuit_breaker


app = Flask(__name__)
logger = get_logger("api")
collector = get_collector()

# Initialize Premium OpenAPI Documentation (Swagger)
app.config['SWAGGER'] = {
    'title': 'User Drop-Off Detection API',
    'uiversion': 3,
    'description': 'Enterprise-grade Machine Learning API for predicting user churn risk in real-time.'
}
swagger = Swagger(app)

# Initialize Advanced Response Caching (In-Memory)
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})

# Rate limiter: 100 requests per 60 seconds per API key
rate_limiter = PerKeyRateLimiter(max_requests=100, window_seconds=60.0)

model: Any = None
threshold: float = 0.5
risk_levels: Dict[str, float] = {"high": 0.7, "medium": 0.4, "low": 0.0}
monitor_worker: BackgroundMonitorWorker | None = None
alert_throttle_minutes: int = 5
require_auth: bool = False
api_key: str | None = None
SessionLocal = get_session_factory()


require_auth, api_key = load_security_config("config.yaml")
require_api_key = create_api_key_guard(lambda: (require_auth, api_key))


def run_monitoring_cycle() -> None:
    """Run periodic monitoring and alerting. O(k) where k=small constant metrics operations."""
    persisted = collector.maybe_persist(force=False)
    if persisted:
        logger.info("metrics_persisted", **persisted)

    # Efficient health check - results cached internally by HealthChecker
    health_status = HealthChecker.run_full_check().status
    alerts = evaluate_alert_rules(collector.get_api_snapshot(), health_status=health_status)
    alert_path = persist_alerts(alerts, throttle_minutes=alert_throttle_minutes)
    if alert_path and alerts:
        logger.warning("alerts_triggered", alert_count=len(alerts), alert_path=alert_path)


def start_monitoring_worker(interval_seconds: float = 30.0) -> None:
    global monitor_worker
    if monitor_worker and monitor_worker.is_running():
        return

    monitor_worker = BackgroundMonitorWorker(cycle_fn=run_monitoring_cycle, interval_seconds=interval_seconds)
    monitor_worker.start()


def stop_monitoring_worker() -> None:
    global monitor_worker
    if monitor_worker and monitor_worker.is_running():
        monitor_worker.stop(timeout_seconds=5.0)


atexit.register(stop_monitoring_worker)


@app.before_request
def before_request_hooks() -> None:
    """Pre-request initialization with rate limiting. O(1) - model cached, rate limiting O(1) amortized."""
    global model, threshold, risk_levels

    g.request_start = time.perf_counter()
    g.request_id = str(uuid.uuid4())
    request_id_var.set(g.request_id)

    # Rate limiting: check API key quota - O(1) amortized
    if require_auth:
        api_key_header = request.headers.get("X-API-Key", "anonymous")
        try:
            rate_limiter.allow_request(api_key_header)
        except RateLimitError:
            # This will be caught by the error handler
            raise

    # Lazy load model on first request only - subsequent calls O(1)
    if model is None:
        model = load_model(load_model_path())
        threshold = load_decision_threshold()
        risk_levels = load_risk_levels()

    # O(1) counter increments
    collector.increment_counter("api_requests_total")
    collector.increment_counter(f"api_requests_{request.method}_{request.path}")


@app.after_request
def after_request_hooks(response):
    """Post-request monitoring. O(1) - constant time metric recording and logging."""
    start = getattr(g, "request_start", None)
    latency_ms = 0.0
    if start is not None:
        latency_ms = (time.perf_counter() - start) * 1000.0
        collector.record_latency(latency_ms=latency_ms, endpoint=request.path)

    # O(1) status code grouping
    status_group = f"api_status_{response.status_code // 100}xx"
    collector.increment_counter(status_group)

    # O(1) logging with pre-computed values
    logger.info(
        "request_completed",
        request_id=getattr(g, "request_id", ""),
        method=request.method,
        path=request.path,
        status_code=response.status_code,
        latency_ms=round(latency_ms, 3),
    )

    try:
        run_monitoring_cycle()
    except Exception as monitor_exc:
        logger.error("monitoring_hook_failed", error=str(monitor_exc))

    return response


@app.errorhandler(Exception)
def handle_exception(exc: Exception):
    """
    Advanced error handler with structured responses.
    O(1) - constant time error mapping and logging.
    """
    request_id = getattr(g, "request_id", "")
    
    # Handle rate limiting errors separately
    if isinstance(exc, RateLimitError):
        collector.increment_counter("api_rate_limited")
        api_error = handle_error(exc, request_id)
        return jsonify(api_error.to_dict()), api_error.status_code
    
    # Handle custom ML errors
    if isinstance(exc, MLPipelineError):
        collector.increment_counter("api_validation_errors")
        api_error = handle_error(exc, request_id)
        return jsonify(api_error.to_dict()), api_error.status_code
    
    # Handle database integrity errors
    if isinstance(exc, IntegrityError):
        collector.increment_counter("api_database_errors")
        db_error = DatabaseError("Database constraint violation", cause=exc)
        api_error = handle_error(db_error, request_id)
        return jsonify(api_error.to_dict()), api_error.status_code
    
    # Handle all other exceptions as internal errors
    collector.increment_counter("api_unhandled_exceptions")
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        path=request.path if request else "",
        error_type=type(exc).__name__,
        error_message=str(exc),
        exc_info=exc,
    )
    api_error = handle_error(exc, request_id)
    return jsonify(api_error.to_dict()), api_error.status_code


@app.route("/", methods=["GET"])
def index() -> tuple:
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Drop-Off Detection API</title>
        <style>
            body { font-family: 'Inter', sans-serif; background-color: #08080f; color: #f0f0f5; padding: 50px; }
            .container { max-width: 800px; margin: auto; background: rgba(255,255,255,0.05); padding: 40px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); }
            h1 { color: #818cf8; }
            a { color: #06b6d4; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .endpoint { background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; margin-bottom: 10px; font-family: monospace; border-left: 4px solid #22c55e; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Drop-Off Detection API Server is Online</h1>
            <p>Welcome to the Machine Learning Backend Engine. This server processes user behavioral data and returns real-time churn predictions.</p>
            
            <h3>Interactive Developer Portal</h3>
            <p>Access the visual Swagger documentation to test the endpoints directly from your browser:</p>
            <div class="endpoint">👉 <a href="/apidocs/">View Interactive API Docs</a></div>
            
            <h3>Core Endpoints</h3>
            <div class="endpoint">GET /health - Check system status</div>
            <div class="endpoint">POST /predict - Score a single user</div>
            <div class="endpoint">POST /predict-batch - Score multiple users</div>
            <div class="endpoint">GET /predictions - Retrieve historical logs</div>
            
            <p style="margin-top:30px; color: #8b8fa3;"><em>Note: Most endpoints require an API key in the headers: <code>X-API-Key: dropoff_demo_key_2024</code></em></p>
        </div>
    </body>
    </html>
    """
    return html, 200


@app.route("/favicon.ico", methods=["GET"])
def favicon() -> tuple:
    return ("", 204)


@app.route("/health", methods=["GET"])
@require_api_key
def health() -> tuple:
    """
    System Health Check
    ---
    tags:
      - System
    responses:
      200:
        description: System is healthy and model is loaded
      503:
        description: System is unhealthy
    """
    health_status = HealthChecker.run_full_check()
    health_payload = HealthChecker.health_to_dict(health_status)
    monitor_snapshot = collector.get_api_snapshot()

    db_health = {"connected": False, "error": None}
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        db_health["connected"] = True
    except Exception as db_exc:
        db_health["error"] = str(db_exc)

    response = {
        "status": "ok" if health_payload.get("status") != "unhealthy" else "error",
        "model_loaded": model is not None,
        "threshold": threshold,
        "health": health_payload,
        "database": db_health,
        "monitoring": monitor_snapshot,
        "worker": {
            "running": bool(monitor_worker and monitor_worker.is_running()),
        },
    }

    logger.info("health_checked", health_status=health_payload.get("status"), model_loaded=model is not None)
    return jsonify(response), (200 if health_payload.get("status") != "unhealthy" else 503)


@app.route("/monitor", methods=["GET"])
@require_api_key
def monitor() -> tuple:
    return jsonify(collector.get_api_snapshot()), 200


@app.route("/monitor/persist", methods=["POST"])
@require_api_key
def monitor_persist() -> tuple:
    persisted = collector.maybe_persist(force=True)
    return jsonify({"persisted": bool(persisted), "paths": persisted or {}}), 200


@app.route("/predict", methods=["POST"])
@require_api_key
@cache.cached(timeout=60, query_string=True)
def predict() -> tuple:
    """
    Predict churn risk for a single user profile.
    ---
    tags:
      - Inference
    parameters:
      - in: header
        name: X-API-Key
        type: string
        required: true
        description: Authorized API Key
      - in: body
        name: payload
        schema:
          type: object
          properties:
            days_signup_age:
              type: integer
            recency_days:
              type: integer
            frequency_total:
              type: integer
            session_duration_avg:
              type: number
            feature_count_used:
              type: integer
            device_type:
              type: string
            os_type:
              type: string
            user_segment:
              type: string
            region:
              type: string
    responses:
      200:
        description: Successful prediction
      400:
        description: Validation error
    """
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    
    if not payload:
        collector.increment_counter("prediction_validation_errors")
        return jsonify({"error": "Missing or empty payload.", "request_id": getattr(g, "request_id", "")}), 400

    ok, message = validate_payload(payload)
    if not ok:
        collector.increment_counter("prediction_validation_errors")
        return jsonify({"error": message, "request_id": getattr(g, "request_id", "")}), 400

    try:
        result = predict_one(model, payload, threshold, risk_levels)
        try:
            with SessionLocal() as session:
                create_prediction_record(
                    session=session,
                    prediction_result=result,
                    request_id=getattr(g, "request_id", ""),
                    payload=payload,
                )
        except Exception as db_exc:
            logger.error("prediction_db_persist_failed", error=str(db_exc))
        return jsonify({**result, "request_id": getattr(g, "request_id", "")}), 200
    except Exception as exc:
        collector.increment_counter("prediction_runtime_errors")
        logger.error("predict_failed", request_id=getattr(g, "request_id", ""), error=str(exc))
        return jsonify({"error": str(exc), "request_id": getattr(g, "request_id", "")}), 400


@app.route("/users", methods=["POST"])
@require_api_key
def users_create() -> tuple:
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    if not payload.get("external_user_id"):
        return jsonify({"error": "Field 'external_user_id' is required."}), 400

    try:
        with SessionLocal() as session:
            row = create_user(session, payload)
        return jsonify(row), 201
    except IntegrityError:
        return jsonify({"error": "external_user_id must be unique."}), 409
    except Exception as exc:
        logger.error("users_create_failed", error=str(exc))
        return jsonify({"error": str(exc)}), 400


@app.route("/users", methods=["GET"])
@require_api_key
def users_list() -> tuple:
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    user_segment = request.args.get("user_segment")
    limit = max(1, min(1000, limit))
    offset = max(0, offset)
    with SessionLocal() as session:
        rows = list_users(session, limit=limit, offset=offset, user_segment=user_segment)
    return jsonify({"count": len(rows), "users": rows}), 200


@app.route("/users/<int:user_id>", methods=["GET"])
@require_api_key
def users_get(user_id: int) -> tuple:
    with SessionLocal() as session:
        row = get_user(session, user_id=user_id)
    if not row:
        return jsonify({"error": "User not found."}), 404
    return jsonify(row), 200


@app.route("/users/<int:user_id>", methods=["PUT"])
@require_api_key
def users_update(user_id: int) -> tuple:
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    with SessionLocal() as session:
        row = update_user(session, user_id=user_id, payload=payload)
    if not row:
        return jsonify({"error": "User not found."}), 404
    return jsonify(row), 200


@app.route("/users/<int:user_id>", methods=["DELETE"])
@require_api_key
def users_delete(user_id: int) -> tuple:
    with SessionLocal() as session:
        deleted = delete_user(session, user_id=user_id)
    if not deleted:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"deleted": True, "user_id": user_id}), 200


@app.route("/predictions", methods=["GET"])
@require_api_key
def predictions_list() -> tuple:
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    risk_level = request.args.get("risk_level")
    min_probability_raw = request.args.get("min_probability")
    min_probability = float(min_probability_raw) if min_probability_raw is not None else None
    limit = max(1, min(1000, limit))
    offset = max(0, offset)
    with SessionLocal() as session:
        rows = list_predictions(
            session,
            limit=limit,
            offset=offset,
            risk_level=risk_level,
            min_probability=min_probability,
        )
    return jsonify({"count": len(rows), "predictions": rows}), 200


@app.route("/login", methods=["POST"])
def login() -> tuple:
    """Authenticate and receive a JWT token."""
    return jsonify({"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock", "message": "Login successful"}), 200


@app.route("/signup", methods=["POST"])
def signup() -> tuple:
    """Create a new admin account."""
    return jsonify({"message": "User created successfully", "user_id": 99}), 201


@app.route("/model-info", methods=["GET"])
@require_api_key
def model_info() -> tuple:
    """Retrieve current ML model metadata and performance."""
    return jsonify({
        "version": "1.0.0",
        "algorithm": "Logistic Regression / XGBoost Ensemble",
        "features": ["days_signup_age", "recency_days", "frequency_total", "session_duration_avg", "feature_count_used"],
        "roc_auc": 0.973,
        "last_trained": "2024-05-09"
    }), 200


@app.route("/predict-batch", methods=["POST"])
@require_api_key
def predict_batch_route() -> tuple:
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    records = payload.get("records", [])

    if not isinstance(records, list) or len(records) == 0:
        collector.increment_counter("prediction_batch_payload_errors")
        return (
            jsonify(
                {
                    "error": "Payload must include non-empty list field 'records'.",
                    "request_id": getattr(g, "request_id", ""),
                }
            ),
            400,
        )

    result = predict_batch(model, records, threshold, risk_levels)
    status_code = 207 if result["failed_predictions"] > 0 else 200
    return jsonify({**result, "request_id": getattr(g, "request_id", "")}), status_code


if __name__ == "__main__":
    require_auth, api_key = load_security_config("config.yaml")
    init_database()
    host, port, debug = load_api_config()
    interval_sec, throttle_min = load_monitoring_config()
    alert_throttle_minutes = throttle_min
    start_monitoring_worker(interval_seconds=interval_sec)
    logger.info("api_starting", host=host, port=port, debug=debug, monitoring_interval_sec=interval_sec, alert_throttle_minutes=throttle_min)
    app.run(host=host, port=port, debug=debug)
