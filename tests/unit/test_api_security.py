import os
import unittest
from unittest.mock import patch

from apps.api.server import JevAPIHandler


class APISecurityTests(unittest.TestCase):
    def test_production_requires_token(self):
        with patch.dict(os.environ, {"JEV_ENV": "production"}, clear=True):
            handler = object.__new__(JevAPIHandler)
            self.assertFalse(handler._authorized())

    def test_bearer_token_is_constant_time_checked(self):
        handler = object.__new__(JevAPIHandler)
        handler.headers = {"Authorization": "Bearer secret"}
        with patch.dict(os.environ, {"JEV_API_TOKEN": "secret"}, clear=True):
            self.assertTrue(handler._authorized())
        handler.headers = {"Authorization": "Bearer wrong"}
        with patch.dict(os.environ, {"JEV_API_TOKEN": "secret"}, clear=True):
            self.assertFalse(handler._authorized())


if __name__ == "__main__":
    unittest.main()
