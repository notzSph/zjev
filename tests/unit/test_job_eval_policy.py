import unittest

from packages.job_eval import derive_job_eval_policy


def _score(value, confidence=0.95):
    return {"score": value, "confidence": confidence}


class JobEvalPolicyTests(unittest.TestCase):
    def test_overclaim_guardrail_overrides_apply_now(self):
        answers = {name: _score(3) for name in (
            "overall_fit", "requirement_coverage", "technical_fit",
            "architecture_fit", "leadership_fit", "client_delivery_fit",
            "quality_and_governance_fit", "seniority_fit", "evidence_quality",
        )}
        answers.update({
            "application_strategy": {"choice": "apply_now", "confidence": 0.95},
            "primary_positioning": {"choice": "direct_match", "confidence": 0.95},
            "critical_requirement_gap": {"noul": 0.0},
            "seniority_mismatch": {"noul": 0.0},
            "overclaim_risk": {"noul": 1.0},
            "resume_tailoring_needed": {"noul": 1.0},
        })
        policy = derive_job_eval_policy({"answers": answers})
        self.assertEqual(policy["recommended_action"], "tailor_first")
        self.assertEqual(policy["confidence_band"], "proceed")

    def test_low_confidence_falls_back_to_manual_review(self):
        answers = {name: _score(4, 0.4) for name in (
            "overall_fit", "requirement_coverage", "technical_fit",
            "architecture_fit", "leadership_fit", "client_delivery_fit",
            "quality_and_governance_fit", "seniority_fit", "evidence_quality",
        )}
        answers.update({
            "application_strategy": {"choice": "apply_now"},
            "primary_positioning": {"choice": "direct_match"},
        })
        policy = derive_job_eval_policy({"answers": answers})
        self.assertEqual(policy["recommended_action"], "manual_review")
        self.assertEqual(policy["confidence_band"], "fallback")


if __name__ == "__main__":
    unittest.main()
