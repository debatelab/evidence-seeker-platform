"""Add embedding and API key tables with pgvector support

Revision ID: d6d80682c265
Revises: 7c237c345803
Create Date: 2025-09-03 12:41:34.551653

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6d80682c265"
down_revision: str | None = "7c237c345803"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create the enum type first
    embedding_status_enum = postgresql.ENUM(
        "PENDING", "PROCESSING", "COMPLETED", "FAILED", name="embeddingstatus"
    )
    embedding_status_enum.create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add embedding-related columns to documents table
    if inspector.has_table("documents"):
        document_columns = {
            column["name"] for column in inspector.get_columns("documents")
        }
        if "embedding_status" not in document_columns:
            op.add_column(
                "documents",
                sa.Column(
                    "embedding_status",
                    embedding_status_enum,
                    default="PENDING",
                    nullable=False,
                ),
            )
        if "embedding_generated_at" not in document_columns:
            op.add_column(
                "documents",
                sa.Column("embedding_generated_at", sa.DateTime(), nullable=True),
            )
        if "embedding_model" not in document_columns:
            op.add_column(
                "documents",
                sa.Column("embedding_model", sa.String(length=100), nullable=True),
            )
        if "embedding_dimensions" not in document_columns:
            op.add_column(
                "documents",
                sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
            )

    # Create embeddings table
    if not inspector.has_table("embeddings"):
        op.create_table(
            "embeddings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("document_uuid", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "embedding_vector", sa.Text(), nullable=False
            ),  # Will be converted to vector type
            sa.Column("model_name", sa.String(length=100), nullable=False),
            sa.Column("chunk_text", sa.Text(), nullable=True),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("total_chunks", sa.Integer(), nullable=False),
            sa.Column("processing_time_ms", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["document_id"], ["documents.id"], name="embeddings_document_id_fkey"
            ),
            sa.ForeignKeyConstraint(
                ["document_uuid"],
                ["documents.uuid"],
                name="embeddings_document_uuid_fkey",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_embeddings_id ON embeddings (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_embeddings_uuid ON embeddings (uuid)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_embeddings_document_id ON embeddings (document_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_embeddings_document_uuid ON embeddings (document_uuid)"
    )

    # Convert text column to vector type and create index
    op.execute(
        """DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'embeddings'
                  AND column_name = 'embedding_vector'
                  AND (data_type <> 'USER-DEFINED' OR udt_name <> 'vector')
            ) THEN
                ALTER TABLE embeddings ALTER COLUMN embedding_vector TYPE vector(768)
                USING embedding_vector::vector(768);
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS embeddings_embedding_vector_idx
        ON embeddings
        USING ivfflat (embedding_vector vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    # Create api_keys table
    if not inspector.has_table("api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("evidence_seeker_id", sa.Integer(), nullable=False),
            sa.Column(
                "evidence_seeker_uuid", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column("encrypted_key", sa.Text(), nullable=False),
            sa.Column("key_hash", sa.String(length=64), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                onupdate=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["evidence_seeker_id"],
                ["evidence_seekers.id"],
                name="api_keys_evidence_seeker_id_fkey",
            ),
            sa.ForeignKeyConstraint(
                ["evidence_seeker_uuid"],
                ["evidence_seekers.uuid"],
                name="api_keys_evidence_seeker_uuid_fkey",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_id ON api_keys (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_uuid ON api_keys (uuid)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_api_keys_evidence_seeker_id ON api_keys (evidence_seeker_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_api_keys_provider ON api_keys (provider)"
    )


def downgrade() -> None:
    # Drop api_keys table
    op.drop_index("ix_api_keys_provider", table_name="api_keys")
    op.drop_index("ix_api_keys_evidence_seeker_id", table_name="api_keys")
    op.drop_index("ix_api_keys_uuid", table_name="api_keys")
    op.drop_index("ix_api_keys_id", table_name="api_keys")
    op.drop_table("api_keys")

    # Drop embeddings table and index
    op.execute("DROP INDEX IF EXISTS embeddings_embedding_vector_idx")
    op.drop_index("ix_embeddings_document_uuid", table_name="embeddings")
    op.drop_index("ix_embeddings_document_id", table_name="embeddings")
    op.drop_index("ix_embeddings_uuid", table_name="embeddings")
    op.drop_index("ix_embeddings_id", table_name="embeddings")
    op.drop_table("embeddings")

    # Remove embedding-related columns from documents table
    op.drop_column("documents", "embedding_dimensions")
    op.drop_column("documents", "embedding_model")
    op.drop_column("documents", "embedding_generated_at")
    op.drop_column("documents", "embedding_status")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS embeddingstatus")

    # Disable pgvector extension (optional - only if no other tables use it)
    # op.execute("DROP EXTENSION IF EXISTS vector")
