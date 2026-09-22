"""Small transport schemas for API-bound payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoreBatchSchema:
    offer: Any
    proof_assets: Any
    candidates: Any
    run_id: Any = None

    @classmethod
    def from_payload(cls, payload: Any) -> "ScoreBatchSchema":
        if not isinstance(payload, dict):
            raise ValueError("request body must be an object")
        return cls(
            offer=payload.get("offer"),
            proof_assets=payload.get("proof_assets"),
            candidates=payload.get("candidates"),
            run_id=payload.get("run_id"),
        )


@dataclass(frozen=True)
class OutcomeSchema:
    audit_id: Any
    outcome: Any
    note: Any = None

    @classmethod
    def from_payload(cls, payload: Any) -> "OutcomeSchema":
        if not isinstance(payload, dict):
            raise ValueError("request body must be an object")
        return cls(payload.get("audit_id"), payload.get("outcome"), payload.get("note"))
