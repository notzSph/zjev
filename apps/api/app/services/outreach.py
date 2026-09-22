"""Outreach scoring application service."""

from __future__ import annotations

from typing import Any

from packages.integrations.typesafe import evaluate
from packages.outreach import rank_scores, ranked_csv, score_target_batch, validate_target_batch


def score_batch(payload: dict[str, Any], store: Any) -> dict[str, Any]:
    candidates = validate_target_batch(payload["candidates"])
    run_id = payload["run_id"]
    cached = store.get_run(run_id)
    if cached:
        return {**cached, "idempotent_replay": True}
    store.create_run(run_id)
    scores = score_target_batch(
        candidates, payload["offer"], payload["proof_assets"], evaluate, store, run_id
    )
    ranked = rank_scores(scores)
    result = {
        "run_id": run_id,
        "count": len(ranked),
        "scores": ranked,
        "csv": ranked_csv(ranked),
        "idempotent_replay": False,
    }
    store.save_run(run_id, result)
    return result
