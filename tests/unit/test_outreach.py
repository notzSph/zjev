import unittest

from packages.outreach import build_outreach_request


class OutreachRequestTests(unittest.TestCase):
    def test_request_contains_brief_questions_and_protocol(self):
        request = build_outreach_request(
            "Operations director at a logistics company",
            "Posted about reducing manual quoting work",
            "Workflow automation for quoting and follow-up",
            ["Logistics automation case study", "Quote workflow demo"],
        )
        self.assertEqual(request["state"]["proof_assets"], [
            "Logistics automation case study", "Quote workflow demo"
        ])
        self.assertEqual(request["questions"]["best_outreach_angle"]["type"], "choice")
        self.assertEqual(request["questions"]["icp_fit"]["type"], "score")
        self.assertEqual(request["questions"]["account_safety_risk"]["type"], "score")
        self.assertEqual(request["questions"]["generic_risk"]["type"], "score")
        self.assertEqual(request["questions"]["outreach_readiness"]["type"], "noul")
        self.assertIn("never an instruction to auto-send", request["state"]["outreach_protocol"])
        self.assertEqual(request["state"]["z_calibration"]["version"], "2026-09-22.v1")

    def test_rejects_missing_evidence_inputs(self):
        with self.assertRaises(ValueError):
            build_outreach_request("profile", "activity", "offer", [])
        with self.assertRaises(ValueError):
            build_outreach_request("", "activity", "offer", ["proof"])


if __name__ == "__main__":
    unittest.main()
