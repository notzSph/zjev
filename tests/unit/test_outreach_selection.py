import unittest

from packages.outreach import build_target_selection_plan


class TargetSelectionTests(unittest.TestCase):
    def test_builds_bounded_human_plan(self):
        plan = build_target_selection_plan(
            "workflow automation", geography="Piedmont, Italy",
            buyer_titles=["COO", "COO", "CTO"],
        )
        self.assertEqual(plan["search"]["buyer_titles"], ["COO", "CTO"])
        self.assertTrue(plan["guardrails"]["low_volume_manual_research"])
        self.assertFalse(plan["guardrails"]["auto_contact"])
        self.assertEqual(plan["guardrails"]["max_candidates_per_batch"], 25)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            build_target_selection_plan("")
        with self.assertRaises(ValueError):
            build_target_selection_plan("automation", buyer_titles=["", "COO"])


if __name__ == "__main__":
    unittest.main()
