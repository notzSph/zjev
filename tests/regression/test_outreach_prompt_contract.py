import unittest

from packages.outreach import build_outreach_request, derive_outreach_policy


class OutreachPromptRegressionTests(unittest.TestCase):
    def test_request_keeps_calibration_and_safety_protocol(self):
        request = build_outreach_request(
            "Business discovered through Google Places: Example SMB",
            "No activity supplied; manual enrichment required",
            "workflow automation",
            ["case study"],
        )
        self.assertIn("Do not invent", request["state"]["outreach_protocol"])
        self.assertIn("icp_fit", request["questions"])
        self.assertEqual(request["state"]["z_calibration"]["version"], "2026-09-22.v1")

    def test_policy_contract_remains_human_review_only(self):
        result = {"answers": {
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
        policy = derive_outreach_policy(result)
        self.assertTrue(policy["human_approval_required"])
        self.assertFalse(policy["auto_send"])


if __name__ == "__main__":
    unittest.main()
