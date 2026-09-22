"""Versioned Outreach persistence models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class OutreachRun(Base):
    __tablename__ = "outreach_runs"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    response: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scores: Mapped[list["OutreachScore"]] = relationship(back_populates="run")


class OutreachScore(Base):
    __tablename__ = "outreach_scores"
    __table_args__ = (Index("ix_outreach_scores_candidate_created", "candidate_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("outreach_runs.run_id"), nullable=True)
    candidate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    calibration_version: Mapped[str] = mapped_column(String(64), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_band: Mapped[str | None] = mapped_column(String(32), nullable=True)
    candidate: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    outcome_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    outcome_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run: Mapped[OutreachRun | None] = relationship(back_populates="scores")


class OutreachJob(Base):
    __tablename__ = "outreach_jobs"
    __table_args__ = (Index("ix_outreach_jobs_status_available", "status", "available_at"),)

    job_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
