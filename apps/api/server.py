#!/usr/bin/env python3
"""Minimal HTTP API for Jev evaluations.

This is intentionally small: one health endpoint and two evaluation endpoints.
The application owns HTTP concerns; the Jev client owns TypeSafe concerns.
"""

from __future__ import annotations

import json
import hmac
import os
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VENDOR = ROOT / ".vendor"
if VENDOR.is_dir() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from packages.core.contracts import InputError  # noqa: E402
from packages.job_fit import build_job_fit_request, derive_job_fit_policy  # noqa: E402
from packages.outreach import (  # noqa: E402
    build_outreach_request,
    build_target_selection_plan,
    derive_outreach_policy,
    OutreachAuditStore,
    score_target_batch,
    rank_scores,
    ranked_csv,
    validate_target_batch,
    import_target_csv,
    search_google_places,
    source_status,
)
from packages.integrations.typesafe import evaluate  # noqa: E402
from apps.api.config import APISettings  # noqa: E402
from apps.api.database import SQLAlchemyAuditStore  # noqa: E402

MAX_BODY_BYTES = 1_000_000


def get_audit_store() -> OutreachAuditStore | SQLAlchemyAuditStore:
    settings = APISettings.from_env()
    if settings.database_url:
        return SQLAlchemyAuditStore(settings.database_url)
    return OutreachAuditStore(settings.audit_db_path)


class JevAPIHandler(BaseHTTPRequestHandler):
    def _request_id(self) -> str:
        return self.headers.get("X-Request-ID", str(uuid.uuid4()))[:128]

    def _authorized(self) -> bool:
        expected = os.environ.get("JEV_API_TOKEN")
        if not expected:
            return os.environ.get("JEV_ENV", "development").lower() != "production"
        authorization = self.headers.get("Authorization", "")
        supplied = authorization.removeprefix("Bearer ").strip()
        return bool(supplied) and hmac.compare_digest(supplied, expected)

    def _json(self, status: int, payload: dict) -> None:
        payload = {"request_id": self._request_id(), **payload}
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._json(200, {"status": "ok"})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            self._json(401, {"error": "unauthorized"})
            return
        if self.path not in {
            "/v1/evaluate", "/v1/job_fit", "/v1/outreach/evaluate",
            "/v1/outreach/target-plan", "/v1/outreach/targets/validate",
            "/v1/outreach/score",
            "/v1/outreach/rank",
            "/v1/outreach/targets/import",
            "/v1/outreach/sources/status", "/v1/outreach/sources/google-places",
            "/v1/outreach/outcomes", "/v1/outreach/metrics", "/v1/outreach/calibration",
        }:
            self._json(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY_BYTES:
                raise InputError("request body must be between 1 byte and 1 MB")
            payload = json.loads(self.rfile.read(length))
            if self.path == "/v1/job_fit":
                result = evaluate(build_job_fit_request(
                    payload.get("cv"),
                    payload.get("job_description"),
                    payload.get("model", "jev-latest"),
                ))
                result["policy"] = derive_job_fit_policy(result)
            elif self.path == "/v1/outreach/evaluate":
                result = evaluate(build_outreach_request(
                    payload.get("target_profile"),
                    payload.get("linkedin_activity"),
                    payload.get("offer"),
                    payload.get("proof_assets"),
                    payload.get("prior_interactions"),
                    payload.get("model", "jev-latest"),
                ))
                result["policy"] = derive_outreach_policy(result)
            elif self.path == "/v1/outreach/target-plan":
                result = build_target_selection_plan(
                    payload.get("offer"),
                    payload.get("geography"),
                    payload.get("company_terms"),
                    payload.get("buyer_titles"),
                    payload.get("priority_signals"),
                )
            elif self.path == "/v1/outreach/targets/validate":
                candidates = validate_target_batch(payload.get("candidates"))
                result = {
                    "count": len(candidates),
                    "candidates": candidates,
                    "ready_for_scoring": True,
                    "vector_indexed": False,
                }
            elif self.path == "/v1/outreach/targets/import":
                candidates = import_target_csv(payload.get("csv"))
                result = {"count": len(candidates), "candidates": candidates, "ready_for_scoring": True}
            elif self.path == "/v1/outreach/sources/status":
                result = source_status()
            elif self.path == "/v1/outreach/sources/google-places":
                api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
                leads = search_google_places(
                    api_key,
                    payload.get("query"),
                    max_results=payload.get("max_results", 20),
                )
                result = {
                    "count": len(leads),
                    "leads": leads,
                    "discovery_only": True,
                    "requires_manual_enrichment": True,
                }
            elif self.path == "/v1/outreach/score":
                candidates = validate_target_batch(payload.get("candidates"))
                audit_store = get_audit_store()
                run_id = payload.get("run_id") or str(uuid.uuid4())
                if not isinstance(run_id, str) or not run_id.strip() or len(run_id) > 128:
                    raise InputError("run_id must be a non-empty string of at most 128 characters")
                cached = audit_store.get_run(run_id)
                if cached is not None:
                    self._json(200, {**cached, "idempotent_replay": True})
                    return
                scores = score_target_batch(
                    candidates,
                    payload.get("offer"),
                    payload.get("proof_assets"),
                    evaluate,
                    audit_store,
                    run_id,
                )
                ranked = rank_scores(scores)
                result = {
                    "run_id": run_id,
                    "count": len(ranked),
                    "scores": ranked,
                    "csv": ranked_csv(ranked),
                    "idempotent_replay": False,
                }
                audit_store.save_run(run_id, result)
            elif self.path == "/v1/outreach/rank":
                ranked = rank_scores(payload.get("scores"))
                result = {"count": len(ranked), "scores": ranked, "csv": ranked_csv(ranked)}
            elif self.path == "/v1/outreach/outcomes":
                audit_store = get_audit_store()
                audit_store.record_outcome(
                    payload.get("audit_id"), payload.get("outcome"), payload.get("note")
                )
                result = {"updated": True}
            elif self.path == "/v1/outreach/metrics":
                audit_store = get_audit_store()
                result = audit_store.metrics()
            elif self.path == "/v1/outreach/calibration":
                audit_store = get_audit_store()
                result = audit_store.calibration_report(payload.get("minimum_labeled", 30))
            else:
                result = evaluate(payload)
            self._json(200, result)
        except (InputError, ValueError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})
        except RuntimeError as error:
            self._json(502, {"error": str(error)})

    def log_message(self, format: str, *args: object) -> None:
        print(format % args, file=sys.stderr)


def main() -> None:
    settings = APISettings.from_env()
    settings.validate()
    server = ThreadingHTTPServer((settings.host, settings.port), JevAPIHandler)
    print(f"Jev API listening on {settings.host}:{settings.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
