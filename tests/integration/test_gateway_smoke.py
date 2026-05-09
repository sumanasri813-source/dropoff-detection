from __future__ import annotations

import json
import os
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - dependency may be absent in some environments
    Draft202012Validator = None


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "docs" / "contracts" / "public-gateway-contract.schema.json"


class GatewaySmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if Draft202012Validator is None:
            raise unittest.SkipTest("jsonschema is not installed. Install with: pip install jsonschema")

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.request_validator = Draft202012Validator(
            {"$ref": "#/$defs/PublicPredictRequest", "$defs": schema["$defs"]}
        )
        cls.response_validator = Draft202012Validator(
            {"$ref": "#/$defs/PublicPredictSuccessResponse", "$defs": schema["$defs"]}
        )

    def test_gateway_predict_roundtrip(self) -> None:
        base_url = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
        url = f"{base_url}/v1/dropoff/predict"

        payload: Dict[str, Any] = {
            "request_id": "f3b1c8a2-8c8b-4f5f-b35c-1c0a0c0f9b12",
            "user": {
                "user_id": "U12345",
                "segment": "free",
                "region": "north",
            },
            "session": {
                "session_id": "S998877",
                "timestamp_utc": "2026-04-08T10:30:00Z",
                "device_type": "mobile",
                "os_type": "android",
            },
            "features": {
                "days_signup_age": 250,
                "recency_days": 45,
                "frequency_total": 9,
                "session_duration_avg": 6.5,
                "feature_count_used": 2,
            },
            "context": {
                "source": "web_app",
                "model_hint": "latest",
            },
        }

        request_errors = list(self.request_validator.iter_errors(payload))
        self.assertEqual(request_errors, [], f"Request schema errors: {[e.message for e in request_errors]}")

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                self.assertEqual(response.status, 200)
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise unittest.SkipTest(f"Gateway not reachable at {url}: {exc}") from exc

        response_errors = list(self.response_validator.iter_errors(body))
        self.assertEqual(response_errors, [], f"Response schema errors: {[e.message for e in response_errors]}")

        self.assertEqual(body["request_id"], payload["request_id"])
        self.assertIn(body["prediction"]["risk_label"], ["low", "medium", "high"])
        self.assertIn("model", body)
        self.assertIn("meta", body)


if __name__ == "__main__":
    unittest.main()