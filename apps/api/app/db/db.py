"""SQLAlchemy audit database adapter."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, create_engine, delete, func, select
from sqlalchemy.orm import sessionmaker

from packages.outreach.audit import POSITIVE_OUTCOMES
from packages.outreach.metrics import classification_metrics, drift_report
from .models.base import Base
from .models import OutreachJob, OutreachRun, OutreachScore
from .session import create_engine_from_url


def _job_dict(job: OutreachJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "status": job.status,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "payload": job.payload,
        "result": job.result,
        "last_error": job.last_error,
        "available_at": job.available_at,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


class SQLAlchemyAuditStore:
    def __init__(self, database_url: str, *, create_schema: bool = False):
        self.engine = (
            create_engine(database_url, future=True)
            if database_url.startswith("sqlite")
            else create_engine_from_url(database_url)
        )
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        if create_schema:
            Base.metadata.create_all(self.engine)

    def record(self, candidate: dict[str, Any], result: dict[str, Any], run_id: str | None = None) -> int:
        policy = result.get("policy")
        if not isinstance(policy, dict):
            raise ValueError("result must contain a policy object")
        score = OutreachScore(
            run_id=run_id, candidate_id=candidate["candidate_id"],
            calibration_version=policy.get("calibration_version", "unknown"),
            recommended_action=policy.get("recommended_action", "unknown"),
            confidence_band=policy.get("confidence_band"), candidate=candidate,
            result=result, policy=policy, created_at=datetime.now(timezone.utc),
        )
        with self.sessions.begin() as session:
            session.add(score)
            session.flush()
            return int(score.id)

    def save_run(self, run_id: str, response: dict[str, Any]) -> None:
        with self.sessions.begin() as session:
            run = session.get(OutreachRun, run_id)
            if run is None:
                session.add(OutreachRun(run_id=run_id, response=response, created_at=datetime.now(timezone.utc)))
            else:
                run.response = response

    def create_run(self, run_id: str) -> None:
        with self.sessions.begin() as session:
            if session.get(OutreachRun, run_id) is None:
                session.add(
                    OutreachRun(
                        run_id=run_id,
                        response={},
                        created_at=datetime.now(timezone.utc),
                    )
                )

    def enqueue_job(self, job_id: str, payload: dict[str, Any], max_attempts: int = 3) -> dict[str, Any]:
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError("job_id must be a non-empty string")
        if not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        with self.sessions.begin() as session:
            if session.get(OutreachJob, job_id) is None:
                now = datetime.now(timezone.utc)
                session.add(
                    OutreachJob(
                        job_id=job_id,
                        status="queued",
                        attempts=0,
                        max_attempts=max_attempts,
                        payload=payload,
                        available_at=now,
                        created_at=now,
                    )
                )
        return self.get_job(job_id)  # type: ignore[return-value]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.sessions() as session:
            job = session.get(OutreachJob, job_id)
            if job is None:
                return None
            return _job_dict(job)

    def claim_job(self, job_id: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        with self.sessions.begin() as session:
            job = session.scalar(
                select(OutreachJob)
                .where(
                    and_(
                        OutreachJob.job_id == job_id,
                        OutreachJob.status == "queued",
                        OutreachJob.available_at <= now,
                    )
                )
                .with_for_update(skip_locked=True)
            )
            if job is None:
                return None
            job.status = "running"
            job.attempts += 1
            job.started_at = now
        return self.get_job(job_id)

    def claim_next_job(self) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        with self.sessions.begin() as session:
            job = session.scalar(
                select(OutreachJob)
                .where(OutreachJob.status == "queued", OutreachJob.available_at <= now)
                .order_by(OutreachJob.available_at, OutreachJob.created_at)
                .with_for_update(skip_locked=True)
            )
            if job is None:
                return None
            job.status = "running"
            job.attempts += 1
            job.started_at = now
            job_id = job.job_id
        return self.get_job(job_id)

    def complete_job(self, job_id: str, result: dict[str, Any]) -> None:
        with self.sessions.begin() as session:
            job = session.get(OutreachJob, job_id)
            if job is not None and job.status == "running":
                job.status = "succeeded"
                job.result = result
                job.completed_at = datetime.now(timezone.utc)

    def fail_job(self, job_id: str, error: str) -> None:
        with self.sessions.begin() as session:
            job = session.get(OutreachJob, job_id)
            if job is None:
                raise ValueError("job_id was not found")
            job.status = "dead_letter" if job.attempts >= job.max_attempts else "queued"
            job.last_error = error[:2000]
            job.available_at = datetime.now(timezone.utc) + timedelta(seconds=2 ** min(job.attempts, 6))

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.sessions() as session:
            run = session.get(OutreachRun, run_id)
            return run.response if run else None

    def record_outcome(self, audit_id: int, outcome: str, note: str | None = None) -> None:
        with self.sessions.begin() as session:
            score = session.get(OutreachScore, audit_id)
            if score is None:
                raise ValueError("audit_id was not found")
            score.outcome = outcome
            score.outcome_note = note.strip() if note else None
            score.outcome_at = datetime.now(timezone.utc)

    def approve_score(self, audit_id: int, decision: str, note: str | None = None) -> None:
        if decision not in {"approved", "rejected", "needs_changes"}:
            raise ValueError("decision must be approved, rejected, or needs_changes")
        if note is not None and not note.strip():
            raise ValueError("approval note must be non-empty when supplied")
        with self.sessions.begin() as session:
            score = session.get(OutreachScore, audit_id)
            if score is None:
                raise ValueError("audit_id was not found")
            score.approval_status = decision
            score.approval_note = note.strip() if note else None
            score.approved_at = datetime.now(timezone.utc)

    def pending_approvals(self, limit: int = 100) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self.sessions() as session:
            rows = session.execute(
                select(
                    OutreachScore.id, OutreachScore.candidate_id,
                    OutreachScore.recommended_action, OutreachScore.confidence_band,
                    OutreachScore.result, OutreachScore.created_at,
                ).where(OutreachScore.approval_status == "pending")
                .order_by(OutreachScore.created_at).limit(limit)
            ).all()
        return [
            {
                "audit_id": audit_id,
                "candidate_id": candidate_id,
                "recommended_action": action,
                "confidence_band": confidence_band,
                "result": result,
                "created_at": created_at,
            }
            for audit_id, candidate_id, action, confidence_band, result, created_at in rows
        ]

    def metrics(self) -> dict[str, Any]:
        with self.sessions() as session:
            total = session.scalar(select(func.count()).select_from(OutreachScore)) or 0
            rows = session.execute(select(OutreachScore.recommended_action, func.count()).group_by(OutreachScore.recommended_action)).all()
            outcomes = session.execute(select(OutreachScore.outcome, func.count()).where(OutreachScore.outcome.is_not(None)).group_by(OutreachScore.outcome)).all()
        return {"total_scores": total, "actions": dict(rows), "outcomes": dict(outcomes)}

    def purge_expired(self, retention_days: int) -> dict[str, int]:
        if not isinstance(retention_days, int) or not 1 <= retention_days <= 3650:
            raise ValueError("retention_days must be between 1 and 3650")
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        with self.sessions.begin() as session:
            scores = session.execute(
                delete(OutreachScore).where(OutreachScore.created_at < cutoff)
            ).rowcount or 0
            runs = session.execute(
                delete(OutreachRun).where(OutreachRun.created_at < cutoff)
            ).rowcount or 0
            jobs = session.execute(
                delete(OutreachJob).where(
                    OutreachJob.created_at < cutoff,
                    OutreachJob.status.in_(("succeeded", "dead_letter")),
                )
            ).rowcount or 0
        return {"scores": scores, "runs": runs, "jobs": jobs}

    def calibration_report(self, minimum_labeled: int = 30) -> dict[str, Any]:
        with self.sessions() as session:
            rows = session.execute(
                select(OutreachScore.recommended_action, OutreachScore.outcome)
                .where(OutreachScore.outcome.is_not(None))
            ).all()
        report = classification_metrics(
            [{"action": action, "outcome": outcome} for action, outcome in rows],
            minimum_labeled,
        )
        return {
            "minimum_labeled": minimum_labeled,
            **report,
            "threshold_tuning_allowed": report["status"] == "ready",
        }

    def drift_report(self, recent_days: int = 7) -> dict[str, Any]:
        with self.sessions() as session:
            rows = session.execute(
                select(
                    OutreachScore.recommended_action,
                    OutreachScore.confidence_band,
                    OutreachScore.policy,
                    OutreachScore.created_at,
                )
            ).all()
        return drift_report(
            [
                {
                    "action": action,
                    "confidence_band": confidence_band or "unknown",
                    "policy": policy,
                    "created_at": created_at,
                }
                for action, confidence_band, policy, created_at in rows
            ],
            recent_days,
        )
