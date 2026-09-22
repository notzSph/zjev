"""Small relational audit store for outreach scoring runs."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

OUTCOME_STATES = {
    "uncontacted", "contacted", "replied", "qualified", "meeting_booked",
    "converted", "not_interested", "disqualified", "no_response",
}
POSITIVE_OUTCOMES = {"replied", "qualified", "meeting_booked", "converted"}


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
                """
                CREATE TABLE IF NOT EXISTS outreach_runs (
                    run_id TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_outreach_scores_candidate "
                "ON outreach_scores(candidate_id, created_at)"
            )
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(outreach_scores)")
            }
            if "outcome" not in columns:
                connection.execute("ALTER TABLE outreach_scores ADD COLUMN outcome TEXT")
            if "outcome_note" not in columns:
                connection.execute("ALTER TABLE outreach_scores ADD COLUMN outcome_note TEXT")
            if "outcome_at" not in columns:
                connection.execute("ALTER TABLE outreach_scores ADD COLUMN outcome_at TEXT")

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

    def record_outcome(self, audit_id: int, outcome: str, note: str | None = None) -> None:
        if not isinstance(audit_id, int) or audit_id <= 0:
            raise ValueError("audit_id must be a positive integer")
        if outcome not in OUTCOME_STATES:
            raise ValueError(f"outcome must be one of: {', '.join(sorted(OUTCOME_STATES))}")
        if note is not None and (not isinstance(note, str) or not note.strip()):
            raise ValueError("outcome note must be a non-empty string when supplied")
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE outreach_scores SET outcome = ?, outcome_note = ?, outcome_at = ? WHERE id = ?",
                (outcome, note.strip() if note else None, datetime.now(timezone.utc).isoformat(), audit_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("audit_id was not found")

    def metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM outreach_scores").fetchone()[0]
            actions = {
                row["recommended_action"]: row["count"]
                for row in connection.execute(
                    "SELECT recommended_action, COUNT(*) AS count "
                    "FROM outreach_scores GROUP BY recommended_action"
                )
            }
            outcomes = {
                row["outcome"]: row["count"]
                for row in connection.execute(
                    "SELECT outcome, COUNT(*) AS count FROM outreach_scores "
                    "WHERE outcome IS NOT NULL GROUP BY outcome"
                )
            }
        return {
            "total_scores": total,
            "actions": actions,
            "outcomes": outcomes,
            "calibration": self.calibration_report(),
        }

    def calibration_report(self, minimum_labeled: int = 30) -> dict[str, Any]:
        if not isinstance(minimum_labeled, int) or minimum_labeled < 1:
            raise ValueError("minimum_labeled must be a positive integer")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT recommended_action, outcome, COUNT(*) AS count "
                "FROM outreach_scores WHERE outcome IS NOT NULL "
                "GROUP BY recommended_action, outcome"
            ).fetchall()
        groups: dict[str, dict[str, int]] = {}
        for row in rows:
            groups.setdefault(row["recommended_action"], {})[row["outcome"]] = row["count"]
        by_action = {}
        for action, counts in groups.items():
            labeled = sum(counts.values())
            positive = sum(count for outcome, count in counts.items() if outcome in POSITIVE_OUTCOMES)
            by_action[action] = {
                "labeled": labeled,
                "positive": positive,
                "positive_rate": round(positive / labeled, 4) if labeled else None,
                "status": "ready" if labeled >= minimum_labeled else "insufficient_data",
                "outcomes": counts,
            }
        return {
            "minimum_labeled": minimum_labeled,
            "by_action": by_action,
            "threshold_tuning_allowed": all(
                item["status"] == "ready" for item in by_action.values()
            ) and bool(by_action),
        }

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT response_json FROM outreach_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return json.loads(row["response_json"]) if row else None

    def save_run(self, run_id: str, response: dict[str, Any]) -> None:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO outreach_runs (run_id, response_json, created_at) VALUES (?, ?, ?)",
                (run_id, json.dumps(response, sort_keys=True), datetime.now(timezone.utc).isoformat()),
            )


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
        result = {
            "candidate_id": candidate["candidate_id"],
            "result": raw,
            "policy": policy,
            "evidence_packet": {
                "items": [
                    {"id": f"{candidate['candidate_id']}:evidence:{index}", "text": text}
                    for index, text in enumerate(candidate.get("evidence", []), start=1)
                ],
                "source_urls": candidate["source_urls"],
                "source_records": candidate["source_records"],
                "freshness_status": _freshness_status(candidate["source_records"]),
                "citation_required": True,
            },
        }
        if audit_store is not None:
            result["audit_id"] = audit_store.record(candidate, result)
        scored.append(result)
    return scored


def _freshness_status(source_records: list[dict[str, Any]], max_age_days: int = 90) -> str:
    timestamps = [record.get("captured_at") for record in source_records if record.get("captured_at")]
    if not timestamps:
        return "unknown"
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    parsed = [datetime.fromisoformat(value) for value in timestamps]
    return "fresh" if max(parsed) >= cutoff else "stale"


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
