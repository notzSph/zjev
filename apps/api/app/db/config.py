"""Validated database URL configuration."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from os import environ
from pathlib import Path

from sqlalchemy.engine import make_url


class PersistenceConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PersistenceSettings:
    database_url: str = field(repr=False)


def normalize_database_url(value: object, *, allow_sqlite: bool = False) -> str:
    if type(value) is not str or not value.strip():
        raise PersistenceConfigurationError("JEV_DATABASE_URL must be a non-empty string")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise PersistenceConfigurationError("JEV_DATABASE_URL contains control characters")
    try:
        url = make_url(value)
    except Exception as error:
        raise PersistenceConfigurationError("JEV_DATABASE_URL is invalid") from error
    if allow_sqlite and url.drivername.startswith("sqlite"):
        return url.render_as_string(hide_password=False)
    if url.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise PersistenceConfigurationError("JEV_DATABASE_URL must use PostgreSQL with psycopg")
    if not url.host or not url.database:
        raise PersistenceConfigurationError("JEV_DATABASE_URL needs a host and database")
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url.render_as_string(hide_password=False)


def persistence_settings_from_env(
    environment: Mapping[str, str] | None = None,
) -> PersistenceSettings:
    source = environ if environment is None else environment
    direct = source.get("JEV_DATABASE_URL")
    file_name = source.get("JEV_DATABASE_URL_FILE") if direct is None else None
    if direct is not None and file_name is not None:
        raise PersistenceConfigurationError("set only one database URL source")
    if file_name is not None:
        try:
            direct = Path(file_name).read_text(encoding="utf-8").rstrip("\r\n")
        except (OSError, UnicodeError) as error:
            raise PersistenceConfigurationError("JEV_DATABASE_URL_FILE could not be read") from error
    return PersistenceSettings(database_url=normalize_database_url(direct))
