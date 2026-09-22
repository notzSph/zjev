import json
import unittest

from packages.outreach import ZCRMClient, export_scores_to_zcrm, score_to_zcrm_lead


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({"count": 1, "created": 1, "updated": 0, "leads": [{"id": "1"}]}).encode()


def _score(eligible=True):
    return {
        "candidate_id": "google-place:ChIJ1",
        "candidate": {
            "candidate_id": "google-place:ChIJ1",
            "company_name": "Example SMB",
            "geography": "Piedmont, Italy",
            "target_profile": "Business discovered through Google Places",
        },
        "eligible": eligible,
        "rank_score": 88.5,
        "policy": {"recommended_action": "draft_for_review"},
        "evidence_packet": {"items": []},
    }


class ZCRMTests(unittest.TestCase):
    def test_maps_account_score_without_person(self):
        lead = score_to_zcrm_lead(_score())
        self.assertEqual(lead["company"], "Example SMB")
        self.assertIsNone(lead["contact_name"])
        self.assertEqual(lead["external_ref"], "google-place:ChIJ1")

    def test_exports_only_eligible_scores_and_sends_batch(self):
        requests = []

        def opener(request, **_kwargs):
            requests.append(request)
            return _Response()

        client = ZCRMClient("https://zcrm.test", "token", "business-1", opener)
        result = export_scores_to_zcrm([_score(), _score(False)], client)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(requests[0].get_header("X-business-id"), "business-1")
        self.assertIn("/api/v1/agent/outreach/leads", requests[0].full_url)


if __name__ == "__main__":
    unittest.main()
