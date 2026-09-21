import unittest

from packages.job_fit import build_job_fit_request


class JobFitRequestTests(unittest.TestCase):
    def test_request_contains_typed_questions(self):
        request = build_job_fit_request("Python consultant", "Solution Architect")
        self.assertEqual(request["state"]["cv"], "Python consultant")
        self.assertEqual(request["state"]["job_description"], "Solution Architect")
        self.assertIn("evaluation_protocol", request["state"])
        self.assertEqual(request["questions"]["overall_fit"]["type"], "score")
        self.assertEqual(request["questions"]["architecture_fit"]["type"], "score")
        self.assertEqual(request["questions"]["evidence_quality"]["type"], "score")
        self.assertEqual(request["questions"]["application_strategy"]["type"], "choice")
        self.assertEqual(request["questions"]["primary_positioning"]["type"], "choice")
        self.assertEqual(request["questions"]["critical_requirement_gap"]["type"], "noul")
        self.assertEqual(request["questions"]["overclaim_risk"]["type"], "noul")

    def test_rejects_empty_inputs(self):
        with self.assertRaises(ValueError):
            build_job_fit_request("", "role")
        with self.assertRaises(ValueError):
            build_job_fit_request("cv", "")
        with self.assertRaises(ValueError):
            build_job_fit_request("cv", "role", "")


if __name__ == "__main__":
    unittest.main()
