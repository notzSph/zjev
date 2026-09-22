"""Small relational audit store for outreach scoring runs."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class OutreachAuditStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self._memory_connection: sqlite3.Connection | None = None
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        if self.path == ":memory:":
            if self._memory_connection is None:
                self._memory_connection = sqlite3.connect(self.path)
                self._memory_connection.row_factory = sqlite3.Row
            return self._memory_connection
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS outreach_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id TEXT NOT NULL,
                    calibration_version TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    confidence_band TEXT,
                    candidate_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    policy_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_outreach_scores_candidate "
                "ON outreach_scores(candidate_id, created_at)"
            )

    def record(self, candidate: dict[str, Any], result: dict[str, Any]) -> int:
        policy = result.get("policy")
        if not isinstance(policy, dict):
            raise ValueError("result must contain a policy object")
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO outreach_scores (
                    candidate_id, calibration_version, recommended_action,
                    confidence_band, candidate_json, result_json, policy_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate["candidate_id"],
                    policy.get("calibration_version", "unknown"),
                    policy.get("recommended_action", "unknown"),
                    policy.get("confidence_band"),
                    json.dumps(candidate, sort_keys=True),
                    json.dumps(result, sort_keys=True),
                    json.dumps(policy, sort_keys=True),
                    created_at,
                ),
            )
            return int(cursor.lastrowid)


def score_target_batch(
    candidates: list[dict[str, Any]],
    offer: str,
    proof_assets: list[str],
    evaluate_fn: Any,
    audit_store: OutreachAuditStore | None = None,
) -> list[dict[str, Any]]:
    """Score a validated batch with one consistent request per candidate."""
    scored = []
    for candidate in candidates:
        request = build_request_for_candidate(candidate, offer, proof_assets)
        raw = evaluate_fn(request)
        if not isinstance(raw, dict):
            raise ValueError("evaluator must return an object")
        policy = derive_policy(raw)
        result = {"candidate_id": candidate["candidate_id"], "result": raw, "policy": policy}
        if audit_store is not None:
            result["audit_id"] = audit_store.record(candidate, result)
        scored.append(result)
    return scored


def build_request_for_candidate(
    candidate: dict[str, Any], offer: str, proof_assets: list[str]
) -> dict[str, Any]:
    from .evaluation import build_outreach_request

    return build_outreach_request(
        candidate["target_profile"],
        candidate["linkedin_activity"],
        offer,
        proof_assets,
        candidate.get("prior_interactions"),
    )


def derive_policy(result: dict[str, Any]) -> dict[str, Any]:
    from .policy import derive_outreach_policy

    return derive_outreach_policy(result)
