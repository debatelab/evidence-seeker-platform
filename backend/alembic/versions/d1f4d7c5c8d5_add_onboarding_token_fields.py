"""add onboarding token metadata and document skip flag

Revision ID: d1f4d7c5c8d5
Revises: 7c237c345803
Create Date: 2025-03-07 12:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d1f4d7c5c8d5"
down_revision = "5fb9f1a0d7b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evidence_seeker_settings",
        sa.Column(
            "document_skip_acknowledged",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "evidence_seeker_settings",
        sa.Column("onboarding_token_jti", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "evidence_seeker_settings",
        sa.Column("onboarding_token_owner_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "evidence_seeker_settings",
        sa.Column("onboarding_token_expires_at", sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        "fk_settings_onboarding_owner",
        "evidence_seeker_settings",
        "users",
        ["onboarding_token_owner_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_settings_onboarding_owner",
        "evidence_seeker_settings",
        type_="foreignkey",
    )
    op.drop_column("evidence_seeker_settings", "onboarding_token_expires_at")
    op.drop_column("evidence_seeker_settings", "onboarding_token_owner_id")
    op.drop_column("evidence_seeker_settings", "onboarding_token_jti")
    op.drop_column("evidence_seeker_settings", "document_skip_acknowledged")
