#!/usr/bin/env python3
"""CLI entry point for the Jev client."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VENDOR = ROOT / ".vendor"
if VENDOR.is_dir() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from packages.jev_client import InputError, evaluate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate typed questions with Jev")
    parser.add_argument("--input", help="JSON request file; defaults to stdin")
    parser.add_argument("--url", help="override the API URL, useful for tests")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()
    try:
        source = open(args.input, encoding="utf-8") if args.input else sys.stdin
        with source:
            payload = json.load(source)
        result = evaluate(payload, url=args.url, timeout=args.timeout, retries=args.retries)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (InputError, RuntimeError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
