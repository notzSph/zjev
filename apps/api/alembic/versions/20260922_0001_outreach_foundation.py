"""Create versioned Outreach persistence tables.

Revision ID: 20260922_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260922_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outreach_runs",
        sa.Column("run_id", sa.String(length=128), primary_key=True),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "outreach_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), sa.ForeignKey("outreach_runs.run_id")),
        sa.Column("candidate_id", sa.String(length=255), nullable=False),
        sa.Column("calibration_version", sa.String(length=64), nullable=False),
        sa.Column("recommended_action", sa.String(length=64), nullable=False),
        sa.Column("confidence_band", sa.String(length=32)),
        sa.Column("candidate", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("policy", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.String(length=32)),
        sa.Column("outcome_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_outreach_scores_candidate_created", "outreach_scores", ["candidate_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_outreach_scores_candidate_created", table_name="outreach_scores")
    op.drop_table("outreach_scores")
    op.drop_table("outreach_runs")
