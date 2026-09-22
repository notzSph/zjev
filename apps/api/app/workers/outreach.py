"""Durable outreach scoring worker."""

from __future__ import annotations

import os
import time
from typing import Any

from packages.outreach import execute_claimed_job

from ..core.config import APISettings
from ..db.db import SQLAlchemyAuditStore
from ..services.outreach import score_batch


def run_once(store: Any) -> bool:
    job = store.claim_next_job()
    if job is None:
        return False
    execute_claimed_job(store, job, lambda payload: score_batch(payload, store))
    return True


def run_forever(store: Any, poll_seconds: float = 2.0) -> None:
    while True:
        if not run_once(store):
            time.sleep(poll_seconds)


def main() -> None:
    settings = APISettings.from_env()
    if not settings.database_url:
        raise RuntimeError("JEV_DATABASE_URL is required for the outreach worker")
    run_forever(SQLAlchemyAuditStore(settings.database_url))


if __name__ == "__main__":
    main()
