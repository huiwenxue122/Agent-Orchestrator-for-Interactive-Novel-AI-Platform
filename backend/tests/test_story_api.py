"""Smoke tests for FastAPI story API."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


class StoryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_root(self) -> None:
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("docs", body)
        self.assertEqual(body["health"], "/health")

    def test_health(self) -> None:
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    def test_turn_ok_status(self) -> None:
        r = self.client.post(
            "/api/story/turn",
            json={
                "session_id": "test-api-session",
                "user_input_text": "A short beat.",
                "user_choice": None,
            },
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["session_id"], "test-api-session")
        self.assertEqual(body["status"], "waiting_for_user")
        self.assertEqual(body["current_node_id"], "wait_for_user")
        self.assertIn("generated_text", body)
        self.assertIn("retry_count", body)


if __name__ == "__main__":
    unittest.main()
