"""Add human approval workflow fields.

Revision ID: 20260922_0003
Revises: 20260922_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260922_0003"
down_revision: str | None = "20260922_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("outreach_scores", sa.Column("approval_status", sa.String(length=32), nullable=False, server_default="pending"))
    op.add_column("outreach_scores", sa.Column("approval_note", sa.Text()))
    op.add_column("outreach_scores", sa.Column("approved_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("outreach_scores", "approved_at")
    op.drop_column("outreach_scores", "approval_note")
    op.drop_column("outreach_scores", "approval_status")
