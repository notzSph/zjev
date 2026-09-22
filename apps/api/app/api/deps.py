"""Shared API dependencies."""

from __future__ import annotations

import hmac
import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from ..core.config import APISettings
from ..db.db import SQLAlchemyAuditStore
from packages.outreach import OutreachAuditStore


def request_id(request: Request, header: str | None = Header(default=None, alias="X-Request-ID")) -> str:
    value = (header or str(uuid.uuid4()))[:128]
    request.state.request_id = value
    return value


def require_auth(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> None:
    settings = APISettings.from_env()
    if not settings.api_token:
        if settings.environment == "production":
            raise HTTPException(status_code=401, detail="unauthorized")
        return
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not supplied or not hmac.compare_digest(supplied, settings.api_token):
        raise HTTPException(status_code=401, detail="unauthorized")


AuthDependency = Annotated[None, Depends(require_auth)]


def get_audit_store() -> OutreachAuditStore | SQLAlchemyAuditStore:
    settings = APISettings.from_env()
    if settings.database_url:
        return SQLAlchemyAuditStore(settings.database_url)
    return OutreachAuditStore(settings.audit_db_path)
