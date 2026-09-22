"""Small durable-job worker contract shared by API queue adapters."""

from __future__ import annotations

from typing import Any, Callable


def process_job(
    store: Any, job_id: str, handler: Callable[[dict[str, Any]], dict[str, Any]]
) -> dict[str, Any] | None:
    """Claim one job, execute it, and persist retry or dead-letter state."""
    job = store.claim_job(job_id)
    if job is None:
        return store.get_job(job_id)
    return execute_claimed_job(store, job, handler)


def execute_claimed_job(
    store: Any, job: dict[str, Any], handler: Callable[[dict[str, Any]], dict[str, Any]]
) -> dict[str, Any] | None:
    try:
        result = handler(job["payload"])
    except Exception as error:
        store.fail_job(job["job_id"], str(error))
        return store.get_job(job["job_id"])
    store.complete_job(job["job_id"], result)
    return store.get_job(job["job_id"])
