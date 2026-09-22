import unittest

from packages.outreach import import_target_csv


class TargetImportTests(unittest.TestCase):
    def test_imports_and_normalizes_csv(self):
        content = (
            "candidate_id,company_name,role,geography,target_profile,linkedin_activity,source_urls,evidence\n"
            "c-1,Example SMB,COO,Piedmont,COO at SMB,Posted about workflows,"
            "https://example.com/profile;https://example.com/company,Recent workflow post||Company page\n"
        )
        result = import_target_csv(content)
        self.assertEqual(result[0]["candidate_id"], "c-1")
        self.assertEqual(len(result[0]["evidence"]), 2)

    def test_rejects_missing_columns(self):
        with self.assertRaises(ValueError):
            import_target_csv("candidate_id,company_name\nc-1,Example\n")


if __name__ == "__main__":
    unittest.main()
