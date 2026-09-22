import unittest
from datetime import datetime, timedelta, timezone

from packages.outreach import classification_metrics, drift_report


class OutreachMetricsTests(unittest.TestCase):
    def test_calculates_precision_recall_from_labeled_outcomes(self):
        report = classification_metrics([
            {"action": "draft_for_review", "outcome": "replied"},
            {"action": "draft_for_review", "outcome": "no_response"},
            {"action": "research_more", "outcome": "converted"},
        ], minimum_labeled=1)
        self.assertEqual(report["true_positive"], 1)
        self.assertEqual(report["false_positive"], 1)
        self.assertEqual(report["false_negative"], 1)
        self.assertEqual(report["precision"], 0.5)
        self.assertEqual(report["recall"], 0.5)

    def test_drift_report_requires_baseline_and_recent_samples(self):
        now = datetime.now(timezone.utc)
        report = drift_report([
            {"action": "research_more", "confidence_band": "review", "policy": {"signals": {"icp_fit": 1}}, "created_at": now - timedelta(days=8)},
            {"action": "draft_for_review", "confidence_band": "proceed", "policy": {"signals": {"icp_fit": 4}}, "created_at": now - timedelta(days=1)},
        ])
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["signal_deltas"]["icp_fit"], 3.0)


if __name__ == "__main__":
    unittest.main()
