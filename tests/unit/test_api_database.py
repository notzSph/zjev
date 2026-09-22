import tempfile
import unittest
from pathlib import Path

from apps.api.app.core.config import APISettings
from apps.api.app.db.db import SQLAlchemyAuditStore


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
            store.create_run("run-1")
            audit_id = store.record(candidate, result, "run-1")
            store.save_run("run-1", {"run_id": "run-1"})
            store.record_outcome(audit_id, "replied")
            self.assertEqual(store.get_run("run-1"), {"run_id": "run-1"})
            self.assertEqual(store.metrics()["outcomes"], {"replied": 1})

    def test_sqlalchemy_job_queue_persists_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLAlchemyAuditStore(
                f"sqlite:///{Path(directory) / 'jobs.db'}", create_schema=True
            )
            store.enqueue_job("job-1", {"run_id": "run-1"}, max_attempts=2)
            job = store.claim_job("job-1")
            self.assertEqual(job["status"], "running")
            store.complete_job("job-1", {"ok": True})
            self.assertEqual(store.get_job("job-1")["status"], "succeeded")


if __name__ == "__main__":
    unittest.main()
