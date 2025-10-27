"""Add original_filename field to documents table

Revision ID: 7c237c345803
Revises: 386798d9f88d
Create Date: 2025-08-26 12:01:00.694520

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c237c345803"
down_revision: str | None = "386798d9f88d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("documents")}
    if "original_filename" not in existing_columns:
        op.add_column(
            "documents",
            sa.Column(
                "original_filename",
                sa.String(length=255),
                nullable=False,
                server_default="unnamed_file",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("documents")}
    if "original_filename" in existing_columns:
        op.drop_column("documents", "original_filename")
