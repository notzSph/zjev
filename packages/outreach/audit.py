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


def _job_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "job_id": row["job_id"],
        "status": row["status"],
        "attempts": row["attempts"],
        "max_attempts": row["max_attempts"],
        "payload": json.loads(row["payload_json"]),
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "last_error": row["last_error"],
        "available_at": row["available_at"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
    }


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
                """
                CREATE TABLE IF NOT EXISTS outreach_jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    payload_json TEXT NOT NULL,
                    result_json TEXT,
                    last_error TEXT,
                    available_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
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

    def record(
        self, candidate: dict[str, Any], result: dict[str, Any], run_id: str | None = None
    ) -> int:
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
            cursor = connection.execute(
                "UPDATE outreach_runs SET response_json = ? WHERE run_id = ?",
                (json.dumps(response, sort_keys=True), run_id),
            )
            if cursor.rowcount == 0:
                connection.execute(
                    "INSERT INTO outreach_runs (run_id, response_json, created_at) VALUES (?, ?, ?)",
                    (run_id, json.dumps(response, sort_keys=True), datetime.now(timezone.utc).isoformat()),
                )

    def create_run(self, run_id: str) -> None:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO outreach_runs (run_id, response_json, created_at) VALUES (?, ?, ?)",
                (run_id, json.dumps({}), datetime.now(timezone.utc).isoformat()),
            )

    def enqueue_job(self, job_id: str, payload: dict[str, Any], max_attempts: int = 3) -> dict[str, Any]:
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError("job_id must be a non-empty string")
        if not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO outreach_jobs "
                "(job_id, status, attempts, max_attempts, payload_json, available_at, created_at) "
                "VALUES (?, 'queued', 0, ?, ?, ?, ?)",
                (job_id, max_attempts, json.dumps(payload, sort_keys=True), now, now),
            )
        return self.get_job(job_id)  # type: ignore[return-value]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM outreach_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        return _job_row(row)

    def claim_job(self, job_id: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        now_text = now.isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE outreach_jobs SET status = 'running', attempts = attempts + 1, "
                "started_at = ? WHERE job_id = ? AND status = 'queued' AND available_at <= ?",
                (now_text, job_id, now_text),
            )
            if cursor.rowcount != 1:
                return None
        return self.get_job(job_id)

    def complete_job(self, job_id: str, result: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE outreach_jobs SET status = 'succeeded', result_json = ?, completed_at = ? "
                "WHERE job_id = ? AND status = 'running'",
                (json.dumps(result, sort_keys=True), datetime.now(timezone.utc).isoformat(), job_id),
            )

    def fail_job(self, job_id: str, error: str) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT attempts, max_attempts FROM outreach_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise ValueError("job_id was not found")
            attempts, max_attempts = row["attempts"], row["max_attempts"]
            terminal = attempts >= max_attempts
            status = "dead_letter" if terminal else "queued"
            available = datetime.now(timezone.utc) + timedelta(seconds=2 ** min(attempts, 6))
            connection.execute(
                "UPDATE outreach_jobs SET status = ?, last_error = ?, available_at = ? WHERE job_id = ?",
                (status, error[:2000], available.isoformat(), job_id),
            )


def score_target_batch(
    candidates: list[dict[str, Any]],
    offer: str,
    proof_assets: list[str],
    evaluate_fn: Any,
    audit_store: OutreachAuditStore | None = None,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    """Score a validated batch with one consistent request per candidate."""
    scored = []
    for candidate in candidates:
        request = build_request_for_candidate(candidate, offer, proof_assets)
        raw = evaluate_fn(request)
        if not isinstance(raw, dict):
            raise ValueError("evaluator must return an object")
        policy = derive_policy(raw)
        evidence_packet = build_evidence_packet(candidate, raw)
        policy = apply_evidence_guardrail(policy, evidence_packet)
        result = {
            "candidate_id": candidate["candidate_id"],
            "result": raw,
            "policy": policy,
            "evidence_packet": evidence_packet,
        }
        if audit_store is not None:
            result["audit_id"] = audit_store.record(candidate, result, run_id)
        scored.append(result)
    return scored


def build_evidence_packet(candidate: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Create a stable evidence catalog and map model-provided citations to it."""
    items = [
        {
            "id": f"{candidate['candidate_id']}:evidence:{index}",
            "text": text,
            "source_url": candidate.get("source_urls", [])[index - 1]
            if index <= len(candidate.get("source_urls", []))
            else None,
        }
        for index, text in enumerate(candidate.get("evidence", []), start=1)
    ]
    valid_ids = {item["id"] for item in items}
    citations: dict[str, list[str]] = {}
    uncited_answers: list[str] = []
    for name, answer in result.get("answers", {}).items():
        if not isinstance(answer, dict):
            uncited_answers.append(name)
            continue
        refs = answer.get("evidence_ids", answer.get("citations", []))
        if not isinstance(refs, list):
            refs = []
        valid_refs = [ref for ref in refs if isinstance(ref, str) and ref in valid_ids]
        citations[name] = valid_refs
        if not valid_refs:
            uncited_answers.append(name)
    contradictions = [
        record.get("contradiction") or record.get("contradicts")
        for record in candidate.get("source_records", [])
        if isinstance(record, dict) and (record.get("contradiction") or record.get("contradicts"))
    ]
    return {
        "items": items,
        "source_urls": candidate.get("source_urls", []),
        "source_records": candidate.get("source_records", []),
        "freshness_status": _freshness_status(candidate.get("source_records", [])),
        "citation_required": True,
        "answer_citations": citations,
        "citation_status": "complete" if not uncited_answers else "missing",
        "uncited_answers": uncited_answers,
        "contradictions": contradictions,
        "contradiction_status": "review" if contradictions else "none_detected",
    }


def apply_evidence_guardrail(policy: dict[str, Any], evidence_packet: dict[str, Any]) -> dict[str, Any]:
    """Force unsupported or contradictory model output into a research state."""
    guarded = dict(policy)
    reasons = []
    if evidence_packet["citation_status"] != "complete":
        reasons.append("missing_answer_citations")
    if evidence_packet["contradiction_status"] == "review":
        reasons.append("contradictory_source_evidence")
    if reasons:
        guarded["model_recommended_action"] = policy.get("recommended_action")
        guarded["recommended_action"] = "research_more"
        guarded["abstained"] = True
        guarded["abstention_reasons"] = reasons
    else:
        guarded["abstained"] = False
        guarded["abstention_reasons"] = []
    return guarded


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
