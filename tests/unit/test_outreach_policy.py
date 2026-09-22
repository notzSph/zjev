import unittest

from packages.outreach import derive_outreach_policy


def _score(value, confidence=0.95):
    return {"score": value, "confidence": confidence}


class OutreachPolicyTests(unittest.TestCase):
    def test_ready_request_is_draft_only(self):
        answers = {
            "icp_fit": _score(4),
            "buyer_relevance": _score(4),
            "buying_signal": _score(4),
            "account_safety_risk": _score(0),
            "personalization_evidence": _score(4),
            "generic_risk": _score(1),
            "outreach_readiness": {"noul": True, "confidence": 0.95},
            "unsupported_claim_risk": {"noul": False},
            "best_outreach_angle": {"choice": "relevant_problem"},
            "cta_type": {"choice": "ask_context"},
        }
        policy = derive_outreach_policy({"answers": answers})
        self.assertEqual(policy["recommended_action"], "draft_for_review")
        self.assertTrue(policy["human_approval_required"])
        self.assertFalse(policy["auto_send"])

    def test_unsupported_claim_forces_review(self):
        answers = {
            "icp_fit": _score(4),
            "buyer_relevance": _score(4),
            "buying_signal": _score(4),
            "account_safety_risk": _score(0),
            "personalization_evidence": _score(4),
            "generic_risk": _score(1),
            "outreach_readiness": {"noul": True, "confidence": 0.95},
            "unsupported_claim_risk": {"noul": True},
            "best_outreach_angle": {"choice": "relevant_result"},
            "cta_type": {"choice": "suggest_conversation"},
        }
        policy = derive_outreach_policy({"answers": answers})
        self.assertEqual(policy["recommended_action"], "human_review")


if __name__ == "__main__":
    unittest.main()
