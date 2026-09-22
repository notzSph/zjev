import tempfile
import unittest
from pathlib import Path

from apps.api.config import APISettings
from apps.api.database import SQLAlchemyAuditStore


class APIDatabaseTests(unittest.TestCase):
    def test_production_settings_require_database_and_token(self):
        settings = APISettings("production", "127.0.0.1", 8080, None, None, "/tmp/audit.db", None)
        with self.assertRaises(RuntimeError):
            settings.validate()

    def test_sqlalchemy_store_persists_run_score_and_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLAlchemyAuditStore(
                f"sqlite:///{Path(directory) / 'outreach.db'}", create_schema=True
            )
            candidate = {"candidate_id": "c-1"}
            result = {
                "policy": {
                    "calibration_version": "test",
                    "recommended_action": "draft_for_review",
                    "confidence_band": "proceed",
                }
            }
            audit_id = store.record(candidate, result)
            store.save_run("run-1", {"run_id": "run-1"})
            store.record_outcome(audit_id, "replied")
            self.assertEqual(store.get_run("run-1"), {"run_id": "run-1"})
            self.assertEqual(store.metrics()["outcomes"], {"replied": 1})


if __name__ == "__main__":
    unittest.main()
