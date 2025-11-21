"""add language column to evidence seekers

Revision ID: aa84b0fa3c0c
Revises: d1f4d7c5c8d5
Create Date: 2025-11-21 09:15:11.484723

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa84b0fa3c0c"
down_revision: str | None = "d1f4d7c5c8d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evidence_seekers",
        sa.Column("language", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evidence_seekers", "language")
