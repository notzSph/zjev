import json
import unittest

from packages.outreach import search_google_places, source_status


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({"places": [{
            "id": "ChIJ1", "displayName": {"text": "Example SMB"},
            "formattedAddress": "Piedmont, Italy",
            "googleMapsUri": "https://maps.google.com/?cid=1",
            "types": ["establishment"],
        }]}).encode()


class SourceTests(unittest.TestCase):
    def test_google_places_returns_discovery_only_leads(self):
        leads = search_google_places("key", "SMBs in Piedmont", opener=lambda *_args, **_kwargs: _Response())
        self.assertEqual(leads[0]["company_name"], "Example SMB")
        self.assertTrue(leads[0]["discovery_only"])
        self.assertEqual(leads[0]["source_records"][0]["source_type"], "google_places")

    def test_source_status_keeps_linkedin_explicitly_manual(self):
        self.assertFalse(source_status()["linkedin"]["available"])
        self.assertEqual(source_status()["csv"]["mode"], "import")


if __name__ == "__main__":
    unittest.main()
