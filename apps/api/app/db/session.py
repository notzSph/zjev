"""SQLAlchemy engine and session boundaries."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import normalize_database_url


def create_engine_from_url(database_url: str) -> Engine:
    return create_engine(normalize_database_url(database_url), pool_pre_ping=True, future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
