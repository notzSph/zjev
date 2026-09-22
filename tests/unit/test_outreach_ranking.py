import unittest

from packages.outreach import rank_scores, ranked_csv


def _score(candidate_id, action, fit):
    return {
        "candidate_id": candidate_id,
        "policy": {
            "recommended_action": action,
            "confidence_band": "proceed",
            "confidence_floor": 0.95,
            "signals": {
                "icp_fit": fit, "buyer_relevance": 4, "buying_signal": 4,
                "personalization_evidence": 4, "generic_risk": 1,
                "account_safety_risk": 0,
            },
        },
    }


class OutreachRankingTests(unittest.TestCase):
    def test_ranks_eligible_candidates_and_exports_csv(self):
        ranked = rank_scores([
            _score("low", "research_more", 4),
            _score("high", "draft_for_review", 4),
        ])
        self.assertEqual([item["candidate_id"] for item in ranked], ["high", "low"])
        self.assertTrue(ranked[0]["eligible"])
        self.assertIn("candidate_id,rank_score", ranked_csv(ranked))

    def test_rejects_missing_policy(self):
        with self.assertRaises(ValueError):
            rank_scores([{"candidate_id": "bad"}])


if __name__ == "__main__":
    unittest.main()
