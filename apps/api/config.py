"""Typed API runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class APISettings:
    environment: str
    host: str
    port: int
    api_token: str | None
    database_url: str | None
    audit_db_path: str
    google_maps_api_key: str | None

    @classmethod
    def from_env(cls) -> "APISettings":
        return cls(
            environment=os.environ.get("JEV_ENV", "development").lower(),
            host=os.environ.get("JEV_API_HOST", "0.0.0.0"),
            port=int(os.environ.get("JEV_API_PORT", "8080")),
            api_token=os.environ.get("JEV_API_TOKEN"),
            database_url=os.environ.get("JEV_DATABASE_URL"),
            audit_db_path=os.environ.get("JEV_OUTREACH_DB", "/tmp/jevzoo-outreach.sqlite3"),
            google_maps_api_key=os.environ.get("GOOGLE_MAPS_API_KEY"),
        )

    def validate(self) -> None:
        if self.environment == "production" and not self.api_token:
            raise RuntimeError("JEV_API_TOKEN is required in production")
        if self.environment == "production" and not self.database_url:
            raise RuntimeError("JEV_DATABASE_URL is required in production")
        if not 1 <= self.port <= 65535:
            raise RuntimeError("JEV_API_PORT must be between 1 and 65535")
