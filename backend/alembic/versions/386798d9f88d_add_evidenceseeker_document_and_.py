"""Add EvidenceSeeker, Document, and Permission models

Revision ID: 386798d9f88d
Revises:
Create Date: 2025-08-25 13:35:09.614870

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "386798d9f88d"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: userrole enum is created by init_db.py, so we skip it here
    # to avoid conflicts during repeated setup runs
    pass

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("email", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("hashed_password", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("is_active", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column("is_superuser", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column("is_verified", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    # Create evidence_seekers table with UUID column
    op.create_table(
        "evidence_seekers",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),  # UUID column
        sa.Column("title", sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column("description", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "logo_url", sa.VARCHAR(length=500), autoincrement=False, nullable=True
        ),
        sa.Column("is_public", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column("created_by", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="evidence_seekers_created_by_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="evidence_seekers_pkey"),
        sa.UniqueConstraint("uuid", name="uq_evidence_seekers_uuid"),
    )
    op.create_index("ix_evidence_seekers_id", "evidence_seekers", ["id"], unique=False)
    op.create_index(
        "ix_evidence_seekers_uuid", "evidence_seekers", ["uuid"], unique=False
    )

    # Create documents table with UUID columns
    op.create_table(
        "documents",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),  # UUID column
        sa.Column("title", sa.VARCHAR(length=200), autoincrement=False, nullable=False),
        sa.Column("description", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "file_path", sa.VARCHAR(length=500), autoincrement=False, nullable=False
        ),
        sa.Column("file_size", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column(
            "mime_type", sa.VARCHAR(length=100), autoincrement=False, nullable=False
        ),
        sa.Column(
            "evidence_seeker_id", sa.INTEGER(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "evidence_seeker_uuid", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["evidence_seeker_id"],
            ["evidence_seekers.id"],
            name="documents_evidence_seeker_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_seeker_uuid"],
            ["evidence_seekers.uuid"],
            name="documents_evidence_seeker_uuid_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="documents_pkey"),
        sa.UniqueConstraint("uuid", name="uq_documents_uuid"),
    )
    op.create_index("ix_documents_id", "documents", ["id"], unique=False)
    op.create_index("ix_documents_uuid", "documents", ["uuid"], unique=False)
    op.create_index(
        "ix_documents_evidence_seeker_uuid",
        "documents",
        ["evidence_seeker_uuid"],
        unique=False,
    )

    # Create permissions table
    op.create_table(
        "permissions",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "evidence_seeker_id", sa.INTEGER(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "role",
            postgresql.ENUM("EVSE_ADMIN", "EVSE_READER", name="userrole"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["evidence_seeker_id"],
            ["evidence_seekers.id"],
            name="permissions_evidence_seeker_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="permissions_user_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="permissions_pkey"),
    )
    op.create_index("ix_permissions_id", "permissions", ["id"], unique=False)


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "evidence_seekers",
        sa.Column(
            "id",
            sa.INTEGER(),
            server_default=sa.text("nextval('evidence_seekers_id_seq'::regclass)"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("title", sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column("description", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "logo_url", sa.VARCHAR(length=500), autoincrement=False, nullable=True
        ),
        sa.Column("is_public", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column("created_by", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="evidence_seekers_created_by_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="evidence_seekers_pkey"),
        postgresql_ignore_search_path=False,
    )
    op.create_index("ix_evidence_seekers_id", "evidence_seekers", ["id"], unique=False)
    op.create_table(
        "permissions",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "evidence_seeker_id", sa.INTEGER(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "role",
            postgresql.ENUM("EVSE_ADMIN", "EVSE_READER", name="userrole"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["evidence_seeker_id"],
            ["evidence_seekers.id"],
            name="permissions_evidence_seeker_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="permissions_user_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="permissions_pkey"),
    )
    op.create_index("ix_permissions_id", "permissions", ["id"], unique=False)
    op.create_table(
        "documents",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("title", sa.VARCHAR(length=200), autoincrement=False, nullable=False),
        sa.Column("description", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "file_path", sa.VARCHAR(length=500), autoincrement=False, nullable=False
        ),
        sa.Column("file_size", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column(
            "mime_type", sa.VARCHAR(length=100), autoincrement=False, nullable=False
        ),
        sa.Column(
            "evidence_seeker_id", sa.INTEGER(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["evidence_seeker_id"],
            ["evidence_seekers.id"],
            name="documents_evidence_seeker_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="documents_pkey"),
    )
    op.create_index("ix_documents_id", "documents", ["id"], unique=False)
    op.create_table(
        "users",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("email", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("hashed_password", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("is_active", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column("is_superuser", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column("is_verified", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    # ### end Alembic commands ###
