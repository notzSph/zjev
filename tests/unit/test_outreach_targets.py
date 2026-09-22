import unittest

from packages.outreach import validate_target_batch


def _candidate(candidate_id="c-1"):
    return {
        "candidate_id": candidate_id,
        "person_name": "A. Target",
        "company_name": "Example SMB",
        "role": "COO",
        "geography": "Piedmont, Italy",
        "target_profile": "COO at an SMB with fragmented quoting workflows",
        "linkedin_activity": "Posted about reducing manual quoting work",
        "evidence": ["Recent post about quoting workflow"],
        "source_urls": ["https://example.com/profile", "https://example.com/profile"],
    }


class TargetBatchTests(unittest.TestCase):
    def test_normalizes_and_deduplicates_sources(self):
        result = validate_target_batch([_candidate()])
        self.assertEqual(result[0]["source_urls"], ["https://example.com/profile"])

    def test_rejects_duplicate_ids_and_missing_evidence_source(self):
        with self.assertRaises(ValueError):
            validate_target_batch([_candidate(), _candidate()])
        candidate = _candidate()
        candidate["source_urls"] = []
        with self.assertRaises(ValueError):
            validate_target_batch([candidate])

    def test_normalizes_source_record_timestamp(self):
        candidate = _candidate()
        candidate["source_records"] = [{
            "url": "https://example.com/profile",
            "captured_at": "2026-09-22T10:00:00+02:00",
            "source_type": "profile",
        }]
        result = validate_target_batch([candidate])[0]
        self.assertEqual(result["source_records"][0]["captured_at"], "2026-09-22T08:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
