from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Dict

from src.api.app import app as flask_app
import src.api.app as api_app_module

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - dependency may be missing in some setups
    Draft202012Validator = None


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "docs" / "contracts" / "public-gateway-contract.schema.json"
FIXTURES_DIR = ROOT / "tests" / "contract" / "fixtures"


class PredictContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if Draft202012Validator is None:
            raise unittest.SkipTest("jsonschema is not installed. Install with: pip install jsonschema")

        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.request_validator = Draft202012Validator(
            {"$ref": "#/$defs/PublicPredictRequest", "$defs": cls.schema["$defs"]}
        )
        cls.success_validator = Draft202012Validator(
            {"$ref": "#/$defs/PublicPredictSuccessResponse", "$defs": cls.schema["$defs"]}
        )
        cls.error_validator = Draft202012Validator(
            {"$ref": "#/$defs/PublicPredictErrorResponse", "$defs": cls.schema["$defs"]}
        )

    def test_public_request_fixture_matches_schema(self) -> None:
        payload = self._load_fixture("public_predict_valid.json")
        errors = list(self.request_validator.iter_errors(payload))
        self.assertEqual(errors, [], f"Schema validation errors: {[e.message for e in errors]}")

    def test_invalid_public_request_fixture_fails_schema(self) -> None:
        payload = self._load_fixture("public_predict_invalid.json")
        errors = list(self.request_validator.iter_errors(payload))
        self.assertGreater(len(errors), 0)

    def test_predict_success_response_matches_schema(self) -> None:
        valid_request = self._load_fixture("public_predict_valid.json")

        original_model = api_app_module.model
        original_predict_one = api_app_module.predict_one
        try:
            api_app_module.model = object()

            def _stub_predict_one(model: Any, payload: Dict[str, Any], threshold: float, risk_levels: Dict[str, float]):
                return {
                    "dropoff_probability": 0.8123,
                    "predicted_label": 1,
                    "risk_level": "high",
                    "threshold_used": 0.5,
                }

            api_app_module.predict_one = _stub_predict_one

            python_payload = {
                "days_signup_age": valid_request["features"]["days_signup_age"],
                "recency_days": valid_request["features"]["recency_days"],
                "frequency_total": valid_request["features"]["frequency_total"],
                "session_duration_avg": valid_request["features"]["session_duration_avg"],
                "feature_count_used": valid_request["features"]["feature_count_used"],
                "device_type": valid_request["session"]["device_type"],
                "os_type": valid_request["session"]["os_type"],
                "user_segment": valid_request["user"]["segment"],
                "region": valid_request["user"]["region"],
            }

            with flask_app.test_client() as client:
                resp = client.post("/predict", json=python_payload)
                self.assertEqual(resp.status_code, 200)
                model_response = resp.get_json()

            public_response = self._to_public_success(valid_request["request_id"], model_response)
            errors = list(self.success_validator.iter_errors(public_response))
            self.assertEqual(errors, [], f"Schema validation errors: {[e.message for e in errors]}")
        finally:
            api_app_module.model = original_model
            api_app_module.predict_one = original_predict_one

    def test_predict_error_response_matches_schema(self) -> None:
        invalid_request = self._load_fixture("public_predict_invalid.json")

        python_payload = {
            "days_signup_age": invalid_request["features"].get("days_signup_age", 10),
            "frequency_total": invalid_request["features"].get("frequency_total", 1),
            "session_duration_avg": invalid_request["features"].get("session_duration_avg", 1),
            "feature_count_used": invalid_request["features"].get("feature_count_used", -1),
            "device_type": invalid_request["session"].get("device_type", "mobile"),
            "os_type": invalid_request["session"].get("os_type", "android"),
            "user_segment": invalid_request["user"].get("segment", "free"),
            "region": invalid_request["user"].get("region", "north"),
        }

        with flask_app.test_client() as client:
            resp = client.post("/predict", json=python_payload)
            self.assertEqual(resp.status_code, 400)
            body = resp.get_json()

        public_error = {
            "request_id": str(body.get("request_id") or invalid_request["request_id"]),
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(body.get("error", "Validation failed")),
                "details": [
                    {"field": "features.feature_count_used", "issue": "must be >= 0"}
                ],
            },
        }

        errors = list(self.error_validator.iter_errors(public_error))
        self.assertEqual(errors, [], f"Schema validation errors: {[e.message for e in errors]}")

    def test_predict_requires_api_key_when_enabled(self) -> None:
        original_require_auth = api_app_module.require_auth
        original_api_key = api_app_module.api_key
        original_model = api_app_module.model
        try:
            api_app_module.require_auth = True
            api_app_module.api_key = "test-key"
            api_app_module.model = object()

            payload = {
                "days_signup_age": 10,
                "recency_days": 2,
                "frequency_total": 20,
                "session_duration_avg": 12.5,
                "feature_count_used": 4,
                "device_type": "mobile",
                "os_type": "android",
                "user_segment": "free",
                "region": "north",
            }

            with flask_app.test_client() as client:
                unauthorized = client.post("/predict", json=payload)
                self.assertEqual(unauthorized.status_code, 401)

                authorized = client.post("/predict", json=payload, headers={"X-API-Key": "test-key"})
                self.assertIn(authorized.status_code, {200, 400})
        finally:
            api_app_module.require_auth = original_require_auth
            api_app_module.api_key = original_api_key
            api_app_module.model = original_model

    def test_predict_batch_requires_api_key_when_enabled(self) -> None:
        original_require_auth = api_app_module.require_auth
        original_api_key = api_app_module.api_key
        original_model = api_app_module.model
        original_predict_batch = api_app_module.predict_batch
        try:
            api_app_module.require_auth = True
            api_app_module.api_key = "test-key"
            api_app_module.model = object()

            def _stub_predict_batch(model: Any, records: list[Dict[str, Any]], threshold: float, risk_levels: Dict[str, float]):
                return {
                    "total_records": len(records),
                    "successful_predictions": len(records),
                    "failed_predictions": 0,
                    "predictions": [
                        {
                            "dropoff_probability": 0.8123,
                            "predicted_label": 1,
                            "risk_level": "high",
                            "threshold_used": 0.5,
                        }
                        for _ in records
                    ],
                    "errors": [],
                }

            api_app_module.predict_batch = _stub_predict_batch

            payload = {
                "records": [
                    {
                        "days_signup_age": 10,
                        "recency_days": 2,
                        "frequency_total": 20,
                        "session_duration_avg": 12.5,
                        "feature_count_used": 4,
                        "device_type": "mobile",
                        "os_type": "android",
                        "user_segment": "free",
                        "region": "north",
                    }
                ]
            }

            with flask_app.test_client() as client:
                unauthorized = client.post("/predict-batch", json=payload)
                self.assertEqual(unauthorized.status_code, 401)

                authorized = client.post("/predict-batch", json=payload, headers={"X-API-Key": "test-key"})
                self.assertEqual(authorized.status_code, 200)
        finally:
            api_app_module.require_auth = original_require_auth
            api_app_module.api_key = original_api_key
            api_app_module.model = original_model
            api_app_module.predict_batch = original_predict_batch

    @staticmethod
    def _to_public_success(request_id: str, model_response: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "request_id": request_id,
            "prediction": {
                "dropoff_probability": model_response["dropoff_probability"],
                "risk_label": model_response["risk_level"],
                "predicted_label": model_response["predicted_label"],
                "threshold_used": model_response["threshold_used"],
                "top_reasons": [
                    {"feature": "recency_days", "impact": 0.31},
                    {"feature": "frequency_total", "impact": 0.24},
                ],
            },
            "model": {
                "model_name": "dropoff_classifier",
                "model_version": "2026.04.08.1",
            },
            "meta": {
                "inference_timestamp_utc": "2026-04-08T10:30:01Z",
                "latency_ms": 23,
            },
        }

    @staticmethod
    def _load_fixture(name: str) -> Dict[str, Any]:
        return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
