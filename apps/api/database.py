"""SQLAlchemy engine, session, and audit store."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from .app.db.base import Base
from .app.db.models import OutreachRun, OutreachScore
from .app.db.session import create_engine_from_url
from packages.outreach.audit import POSITIVE_OUTCOMES


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
            run_id=run_id,
            candidate_id=candidate["candidate_id"],
            calibration_version=policy.get("calibration_version", "unknown"),
            recommended_action=policy.get("recommended_action", "unknown"),
            confidence_band=policy.get("confidence_band"),
            candidate=candidate,
            result=result,
            policy=policy,
            created_at=datetime.now(timezone.utc),
        )
        with self.sessions.begin() as session:
            session.add(score)
            session.flush()
            return int(score.id)

    def save_run(self, run_id: str, response: dict[str, Any]) -> None:
        with self.sessions.begin() as session:
            session.add(OutreachRun(
                run_id=run_id,
                response=response,
                created_at=datetime.now(timezone.utc),
            ))

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

    def metrics(self) -> dict[str, Any]:
        with self.sessions() as session:
            total = session.scalar(select(func.count()).select_from(OutreachScore)) or 0
            rows = session.execute(
                select(OutreachScore.recommended_action, func.count())
                .group_by(OutreachScore.recommended_action)
            ).all()
            outcomes = session.execute(
                select(OutreachScore.outcome, func.count())
                .where(OutreachScore.outcome.is_not(None))
                .group_by(OutreachScore.outcome)
            ).all()
        return {
            "total_scores": total,
            "actions": {action: count for action, count in rows},
            "outcomes": {outcome: count for outcome, count in outcomes},
        }

    def calibration_report(self, minimum_labeled: int = 30) -> dict[str, Any]:
        with self.sessions() as session:
            rows = session.execute(
                select(OutreachScore.recommended_action, OutreachScore.outcome, func.count())
                .where(OutreachScore.outcome.is_not(None))
                .group_by(OutreachScore.recommended_action, OutreachScore.outcome)
            ).all()
        groups: dict[str, dict[str, int]] = {}
        for action, outcome, count in rows:
            groups.setdefault(action, {})[outcome] = count
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
