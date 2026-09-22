"""Compatibility exports. Canonical models live under ``app.db.models``."""

from .app.db.base import Base
from .app.db.models import OutreachRun, OutreachScore

__all__ = ["Base", "OutreachRun", "OutreachScore"]
