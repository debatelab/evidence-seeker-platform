"""Add embedding backend fields to evidence seeker settings

Revision ID: 5fb9f1a0d7b3
Revises: 1f5a9e2b4c7d
Create Date: 2025-03-18 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5fb9f1a0d7b3"
down_revision: str | None = "1f5a9e2b4c7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evidence_seeker_settings",
        sa.Column(
            "embed_backend_type",
            sa.String(length=50),
            nullable=False,
            server_default="huggingface",
        ),
    )
    op.add_column(
        "evidence_seeker_settings",
        sa.Column("embed_base_url", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "evidence_seeker_settings",
        sa.Column("embed_bill_to", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "evidence_seeker_settings",
        sa.Column("trust_remote_code", sa.Boolean(), nullable=True),
    )

    op.execute(
        "UPDATE evidence_seeker_settings SET embed_backend_type = 'huggingface' "
        "WHERE embed_backend_type IS NULL"
    )
    op.alter_column(
        "evidence_seeker_settings",
        "embed_backend_type",
        server_default=None,
        existing_type=sa.String(length=50),
    )


def downgrade() -> None:
    op.drop_column("evidence_seeker_settings", "trust_remote_code")
    op.drop_column("evidence_seeker_settings", "embed_bill_to")
    op.drop_column("evidence_seeker_settings", "embed_base_url")
    op.drop_column("evidence_seeker_settings", "embed_backend_type")
