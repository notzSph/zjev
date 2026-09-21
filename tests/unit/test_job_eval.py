import unittest

from packages.evaluations import build_job_eval_request


class JobEvalRequestTests(unittest.TestCase):
    def test_request_contains_typed_questions(self):
        request = build_job_eval_request("Python consultant", "Solution Architect")
        self.assertEqual(request["state"], {"cv": "Python consultant", "job_description": "Solution Architect"})
        self.assertEqual(request["questions"]["overall_fit"]["type"], "score")
        self.assertEqual(request["questions"]["application_strategy"]["type"], "choice")
        self.assertEqual(request["questions"]["overclaim_risk"]["type"], "noul")

    def test_rejects_empty_inputs(self):
        with self.assertRaises(ValueError):
            build_job_eval_request("", "role")
        with self.assertRaises(ValueError):
            build_job_eval_request("cv", "")


if __name__ == "__main__":
    unittest.main()
