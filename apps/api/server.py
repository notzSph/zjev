#!/usr/bin/env python3
"""Minimal HTTP API for Jev evaluations.

This is intentionally small: one health endpoint and two evaluation endpoints.
The application owns HTTP concerns; the Jev client owns TypeSafe concerns.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VENDOR = ROOT / ".vendor"
if VENDOR.is_dir() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from packages.core.contracts import InputError  # noqa: E402
from packages.job_eval import build_job_eval_request, derive_job_eval_policy  # noqa: E402
from packages.integrations.typesafe import evaluate  # noqa: E402

MAX_BODY_BYTES = 1_000_000


class JevAPIHandler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
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
        if self.path not in {"/v1/evaluate", "/v1/job_eval"}:
            self._json(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY_BYTES:
                raise InputError("request body must be between 1 byte and 1 MB")
            payload = json.loads(self.rfile.read(length))
            if self.path == "/v1/job_eval":
                result = evaluate(build_job_eval_request(
                    payload.get("cv"),
                    payload.get("job_description"),
                    payload.get("model", "jev-latest"),
                ))
                result["policy"] = derive_job_eval_policy(result)
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
    host = os.environ.get("JEV_API_HOST", "0.0.0.0")
    port = int(os.environ.get("JEV_API_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), JevAPIHandler)
    print(f"Jev API listening on {host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
