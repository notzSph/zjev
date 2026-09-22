import unittest

from packages.outreach import OutreachAuditStore, score_target_batch, validate_target_batch


def _candidate():
    return validate_target_batch([{
        "candidate_id": "c-1",
        "company_name": "Example SMB",
        "role": "COO",
        "geography": "Piedmont, Italy",
        "target_profile": "COO at a logistics SMB",
        "linkedin_activity": "Posted about manual quoting",
        "source_urls": ["https://example.com/profile"],
    }])[0]


def _evaluation(_request):
    return {"answers": {
        "icp_fit": {"score": 4, "confidence": 0.95},
        "buyer_relevance": {"score": 4, "confidence": 0.95},
        "buying_signal": {"score": 4, "confidence": 0.95},
        "account_safety_risk": {"score": 0, "confidence": 0.95},
        "personalization_evidence": {"score": 4, "confidence": 0.95},
        "generic_risk": {"score": 1, "confidence": 0.95},
        "outreach_readiness": {"noul": True, "confidence": 0.95},
        "unsupported_claim_risk": {"noul": False},
        "best_outreach_angle": {"choice": "relevant_problem"},
        "cta_type": {"choice": "ask_context"},
    }}


class OutreachAuditTests(unittest.TestCase):
    def test_scores_and_records_batch(self):
        store = OutreachAuditStore(":memory:")
        result = score_target_batch([_candidate()], "workflow automation", ["case study"], _evaluation, store)
        self.assertEqual(result[0]["policy"]["recommended_action"], "draft_for_review")
        self.assertEqual(result[0]["audit_id"], 1)
        self.assertTrue(result[0]["evidence_packet"]["citation_required"])

    def test_records_outcome_and_metrics(self):
        store = OutreachAuditStore(":memory:")
        result = score_target_batch([_candidate()], "workflow automation", ["case study"], _evaluation, store)
        store.record_outcome(result[0]["audit_id"], "replied", "Asked for more context")
        self.assertEqual(store.metrics()["outcomes"], {"replied": 1})

    def test_rejects_unknown_outcome(self):
        store = OutreachAuditStore(":memory:")
        with self.assertRaises(ValueError):
            store.record_outcome(1, "maybe")

    def test_stores_and_replays_run_response(self):
        store = OutreachAuditStore(":memory:")
        response = {"run_id": "run-1", "count": 1, "scores": []}
        store.save_run("run-1", response)
        self.assertEqual(store.get_run("run-1"), response)
        with self.assertRaises(ValueError):
            store.save_run("", response)


if __name__ == "__main__":
    unittest.main()
