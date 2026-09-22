#!/usr/bin/env python3
"""Thin development launcher for the modular FastAPI application."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = Path(__file__).resolve().parent
for path in (ROOT, API_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import uvicorn  # noqa: E402

from app.main import app  # noqa: E402

__all__ = ["app"]


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("JEV_API_PORT", "8080")))
