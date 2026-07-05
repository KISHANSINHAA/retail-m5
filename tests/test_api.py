"""
Integration tests for FastAPI REST endpoints.
"""
from __future__ import annotations

import unittest
from fastapi.testclient import TestClient
from api.main import app


class TestRetailSenseAPI(unittest.TestCase):
    """Test suite for validating backend server endpoints."""

    def setUp(self):
        self.client = TestClient(app)

    def test_01_etl_status_endpoint(self):
        """Verify etl/status responds correctly."""
        response = self.client.get("/api/etl/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("tables_exist", data)
        self.assertIn("model_exists", data)


if __name__ == "__main__":
    unittest.main()
