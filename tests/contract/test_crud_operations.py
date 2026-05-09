from __future__ import annotations

import unittest
from typing import Any, Dict

from src.api import app as api_app_module
from src.api.app import app as flask_app
from src.db import connection


class CrudContractTests(unittest.TestCase):
    def setUp(self) -> None:
        """Initialize Flask test client with in-memory SQLite database."""
        self.original_get_database_url = connection.get_database_url
        self.original_get_engine = connection.get_engine
        self.original_get_session_factory = connection.get_session_factory

        connection.get_database_url.cache_clear()
        connection.get_engine.cache_clear()
        connection.get_session_factory.cache_clear()

        in_memory_db_url = "sqlite:///:memory:"

        def mock_get_database_url() -> str:
            return in_memory_db_url

        connection.get_database_url = mock_get_database_url
        connection.get_engine.cache_clear()
        connection.get_session_factory.cache_clear()

        api_app_module.SessionLocal = connection.get_session_factory()
        connection.init_database()
        self.client = flask_app.test_client()

    def tearDown(self) -> None:
        """Restore original DB connection and auth flags."""
        connection.get_database_url = self.original_get_database_url
        connection.get_engine = self.original_get_engine
        connection.get_session_factory = self.original_get_session_factory
        connection.get_database_url.cache_clear()
        connection.get_engine.cache_clear()
        connection.get_session_factory.cache_clear()
        api_app_module.require_auth = False
        api_app_module.api_key = None

    def test_users_create_success(self) -> None:
        payload = {"external_user_id": "user_001", "email": "user@example.com", "user_segment": "premium"}
        resp = self.client.post("/users", json=payload)

        self.assertEqual(resp.status_code, 201, f"Response: {resp.get_json()}")
        body = resp.get_json()
        self.assertIn("id", body)
        self.assertEqual(body["external_user_id"], "user_001")
        self.assertEqual(body["email"], "user@example.com")

    def test_users_create_missing_external_user_id(self) -> None:
        resp = self.client.post("/users", json={"email": "user@example.com"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    def test_users_create_duplicate_external_user_id(self) -> None:
        payload = {"external_user_id": "user_001", "email": "user@example.com"}
        first = self.client.post("/users", json=payload)
        second = self.client.post("/users", json=payload)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)

    def test_users_list_empty(self) -> None:
        resp = self.client.get("/users")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()

        self.assertEqual(body["count"], 0)
        self.assertEqual(len(body["users"]), 0)

    def test_users_list_with_data(self) -> None:
        self.client.post("/users", json={"external_user_id": "user_001", "email": "user1@example.com"})
        self.client.post("/users", json={"external_user_id": "user_002", "email": "user2@example.com"})

        resp = self.client.get("/users")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(len(body["users"]), 2)

    def test_users_list_with_limit(self) -> None:
        for i in range(5):
            self.client.post("/users", json={"external_user_id": f"user_{i:03d}"})

        resp = self.client.get("/users?limit=2")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(len(body["users"]), 2)

    def test_users_list_with_segment_filter(self) -> None:
        self.client.post("/users", json={"external_user_id": "u1", "user_segment": "free"})
        self.client.post("/users", json={"external_user_id": "u2", "user_segment": "premium"})

        resp = self.client.get("/users?user_segment=premium")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["users"][0]["user_segment"], "premium")

    def test_users_get_success(self) -> None:
        created = self.client.post("/users", json={"external_user_id": "user_001", "email": "user@example.com"})
        user_id = created.get_json()["id"]

        resp = self.client.get(f"/users/{user_id}")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["id"], user_id)
        self.assertEqual(body["external_user_id"], "user_001")

    def test_users_get_not_found(self) -> None:
        resp = self.client.get("/users/9999")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("error", resp.get_json())

    def test_users_update_success(self) -> None:
        created = self.client.post("/users", json={"external_user_id": "user_001", "email": "user@example.com"})
        user_id = created.get_json()["id"]

        resp = self.client.put(f"/users/{user_id}", json={"email": "newemail@example.com", "user_segment": "trial"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["email"], "newemail@example.com")
        self.assertEqual(body["user_segment"], "trial")

    def test_users_update_not_found(self) -> None:
        resp = self.client.put("/users/9999", json={"email": "newemail@example.com"})
        self.assertEqual(resp.status_code, 404)

    def test_users_delete_success(self) -> None:
        created = self.client.post("/users", json={"external_user_id": "user_001", "email": "user@example.com"})
        user_id = created.get_json()["id"]

        deleted = self.client.delete(f"/users/{user_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.get_json()["deleted"])

        get_resp = self.client.get(f"/users/{user_id}")
        self.assertEqual(get_resp.status_code, 404)

    def test_users_delete_not_found(self) -> None:
        resp = self.client.delete("/users/9999")
        self.assertEqual(resp.status_code, 404)

    def test_predictions_list_empty(self) -> None:
        resp = self.client.get("/predictions")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["count"], 0)
        self.assertIsInstance(body["predictions"], list)

    def test_predictions_list_with_filters(self) -> None:
        self.client.post("/users", json={"external_user_id": "pred_user_1", "user_segment": "free"})

        original_model = api_app_module.model
        original_predict_one = api_app_module.predict_one
        try:
            api_app_module.model = object()

            def _stub_predict_one(
                _model: Any,
                _payload: Dict[str, Any],
                _threshold: float,
                _risk_levels: Dict[str, float],
            ) -> Dict[str, Any]:
                return {
                    "dropoff_probability": 0.85,
                    "predicted_label": 1,
                    "risk_level": "high",
                    "threshold_used": 0.5,
                }

            api_app_module.predict_one = _stub_predict_one
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
                "external_user_id": "pred_user_1",
            }
            predict_resp = self.client.post("/predict", json=payload)
            self.assertEqual(predict_resp.status_code, 200)
        finally:
            api_app_module.model = original_model
            api_app_module.predict_one = original_predict_one

        resp = self.client.get("/predictions?risk_level=high&min_probability=0.8")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertGreaterEqual(body["count"], 1)
        self.assertEqual(body["predictions"][0]["risk_level"], "high")

    def test_db_endpoints_require_api_key_when_enabled(self) -> None:
        api_app_module.require_auth = True
        api_app_module.api_key = "test-key"

        unauthorized = self.client.get("/users")
        self.assertEqual(unauthorized.status_code, 401)

        authorized = self.client.get("/users", headers={"X-API-Key": "test-key"})
        self.assertEqual(authorized.status_code, 200)

    def test_monitor_endpoints_require_api_key_when_enabled(self) -> None:
        api_app_module.require_auth = True
        api_app_module.api_key = "test-key"

        health_unauthorized = self.client.get("/health")
        self.assertEqual(health_unauthorized.status_code, 401)
        health_authorized = self.client.get("/health", headers={"X-API-Key": "test-key"})
        self.assertEqual(health_authorized.status_code, 200)

        monitor_unauthorized = self.client.get("/monitor")
        self.assertEqual(monitor_unauthorized.status_code, 401)
        monitor_authorized = self.client.get("/monitor", headers={"X-API-Key": "test-key"})
        self.assertEqual(monitor_authorized.status_code, 200)

        persist_unauthorized = self.client.post("/monitor/persist")
        self.assertEqual(persist_unauthorized.status_code, 401)
        persist_authorized = self.client.post("/monitor/persist", headers={"X-API-Key": "test-key"})
        self.assertEqual(persist_authorized.status_code, 200)

    def test_users_crud_full_workflow(self) -> None:
        create_resp = self.client.post(
            "/users",
            json={
                "external_user_id": "workflow_user",
                "email": "workflow@example.com",
                "user_segment": "free",
                "device_type": "mobile",
                "os_type": "android",
                "region": "north",
            },
        )
        self.assertEqual(create_resp.status_code, 201)
        user_id = create_resp.get_json()["id"]

        get_resp = self.client.get(f"/users/{user_id}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.get_json()["external_user_id"], "workflow_user")

        update_resp = self.client.put(f"/users/{user_id}", json={"user_segment": "premium", "region": "south"})
        self.assertEqual(update_resp.status_code, 200)
        updated = update_resp.get_json()
        self.assertEqual(updated["user_segment"], "premium")
        self.assertEqual(updated["region"], "south")

        list_resp = self.client.get("/users")
        self.assertEqual(list_resp.status_code, 200)
        self.assertGreaterEqual(list_resp.get_json()["count"], 1)

        delete_resp = self.client.delete(f"/users/{user_id}")
        self.assertEqual(delete_resp.status_code, 200)
        self.assertTrue(delete_resp.get_json()["deleted"])

        final_get = self.client.get(f"/users/{user_id}")
        self.assertEqual(final_get.status_code, 404)


if __name__ == "__main__":
    unittest.main()