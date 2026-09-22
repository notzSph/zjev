import os
import unittest
from unittest.mock import patch

from apps.api.app.api.dependencies import require_auth
from fastapi import HTTPException


class APISecurityTests(unittest.TestCase):
    def test_production_requires_token(self):
        with patch.dict(os.environ, {"JEV_ENV": "production"}, clear=True):
            with self.assertRaises(HTTPException):
                require_auth(None)

    def test_bearer_token_is_checked(self):
        with patch.dict(os.environ, {"JEV_API_TOKEN": "secret"}, clear=True):
            require_auth("Bearer secret")
            with self.assertRaises(HTTPException):
                require_auth("Bearer wrong")
