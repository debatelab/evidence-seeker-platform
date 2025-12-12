"""add optional source_url to documents

Revision ID: 3a5edc6f8c9b
Revises: d1f4d7c5c8d5
Create Date: 2025-03-10 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3a5edc6f8c9b"
down_revision = "aa84b0fa3c0c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("source_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "source_url")
