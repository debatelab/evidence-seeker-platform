"""Introduce EvidenceSeeker library tables and remove legacy embedding structures

Revision ID: 1f5a9e2b4c7d
Revises: d6d80682c265
Create Date: 2025-03-15 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1f5a9e2b4c7d"
down_revision: str | None = "d6d80682c265"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop legacy embedding table and related metadata
    op.drop_table("embeddings")

    with op.batch_alter_table("documents") as batch_op:
        for column in (
            "embedding_status",
            "embedding_generated_at",
            "embedding_model",
            "embedding_dimensions",
        ):
            batch_op.drop_column(column)
        batch_op.add_column(
            sa.Column("index_file_key", sa.String(length=255), nullable=True)
        )

    op.execute("DROP TYPE IF EXISTS embeddingstatus")

    # Create enums for new tables
    fact_check_run_status = postgresql.ENUM(
        "PENDING",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
        "CANCELLED",
        name="fact_check_run_status",
        create_type=False,
    )
    fact_check_run_status.create(op.get_bind(), checkfirst=True)

    # Create custom enum types for fact-checking
    interpretation_type = postgresql.ENUM(
        "descriptive",
        "ascriptive",
        "normative",
        name="fact_check_interpretation_type",
        create_type=False,
    )
    interpretation_type.create(op.get_bind(), checkfirst=True)

    confirmation_level = postgresql.ENUM(
        "strongly_confirmed",
        "confirmed",
        "weakly_confirmed",
        "inconclusive_confirmation",
        "weakly_disconfirmed",
        "disconfirmed",
        "strongly_disconfirmed",
        name="fact_check_confirmation_level",
        create_type=False,
    )
    confirmation_level.create(op.get_bind(), checkfirst=True)

    evidence_stance = postgresql.ENUM(
        "SUPPORTS",
        "REFUTES",
        "NEUTRAL",
        name="fact_check_evidence_stance",
        create_type=False,
    )
    evidence_stance.create(op.get_bind(), checkfirst=True)

    fact_check_run_visibility = postgresql.ENUM(
        "PUBLIC",
        "UNLISTED",
        "PRIVATE",
        name="fact_check_run_visibility",
        create_type=False,
    )
    fact_check_run_visibility.create(op.get_bind(), checkfirst=True)

    publication_mode = postgresql.ENUM(
        "AUTOPUBLISH",
        "MANUAL",
        name="fact_check_publication_mode",
        create_type=False,
    )
    publication_mode.create(op.get_bind(), checkfirst=True)

    index_job_status = postgresql.ENUM(
        "QUEUED",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
        "CANCELLED",
        name="index_job_status",
        create_type=False,
    )
    index_job_status.create(op.get_bind(), checkfirst=True)

    # Evidence seeker settings table
    op.create_table(
        "evidence_seeker_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evidence_seeker_id", sa.Integer(), nullable=False),
        sa.Column("huggingface_api_key_id", sa.Integer(), nullable=True),
        sa.Column("default_model", sa.String(length=150), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=True),
        sa.Column("rerank_k", sa.Integer(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column(
            "metadata_filters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_overrides",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "setup_mode",
            sa.String(length=16),
            nullable=False,
            server_default="SIMPLE",
        ),
        sa.Column(
            "configuration_state",
            sa.String(length=32),
            nullable=False,
            server_default="UNCONFIGURED",
        ),
        sa.Column("configured_at", sa.DateTime(), nullable=True),
        sa.Column(
            "missing_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("last_validated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
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
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["evidence_seeker_id"],
            ["evidence_seekers.id"],
            name="evidence_seeker_settings_seeker_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["huggingface_api_key_id"],
            ["api_keys.id"],
            name="evidence_seeker_settings_api_key_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="evidence_seeker_settings_updated_by_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evidence_seeker_id", name="uq_evidence_seeker_settings_seeker"
        ),
    )

    with op.batch_alter_table("evidence_seekers") as batch_op:
        batch_op.add_column(
            sa.Column(
                "fact_check_publication_mode",
                publication_mode,
                nullable=False,
                server_default="AUTOPUBLISH",
            )
        )

    # Fact-check tables
    op.create_table(
        "fact_check_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_seeker_id", sa.Integer(), nullable=False),
        sa.Column("submitted_by", sa.Integer(), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", fact_check_run_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("operation_id", sa.String(length=64), nullable=True),
        sa.Column(
            "config_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "visibility",
            fact_check_run_visibility,
            nullable=False,
            server_default="PUBLIC",
        ),
        sa.Column("featured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("featured_by_id", sa.Integer(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.Integer(), nullable=True),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("began_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["evidence_seeker_id"],
            ["evidence_seekers.id"],
            name="fact_check_runs_seeker_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"], ["users.id"], name="fact_check_runs_submitted_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["featured_by_id"], ["users.id"], name="fact_check_runs_featured_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by_id"], ["users.id"], name="fact_check_runs_deleted_by_fkey"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )

    op.create_table(
        "index_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_seeker_id", sa.Integer(), nullable=False),
        sa.Column("submitted_by", sa.Integer(), nullable=False),
        sa.Column("document_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", index_job_status, nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("operation_id", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["evidence_seeker_id"],
            ["evidence_seekers.id"],
            name="index_jobs_seeker_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"], ["users.id"], name="index_jobs_submitted_by_fkey"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )

    op.create_table(
        "fact_check_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("interpretation_index", sa.Integer(), nullable=False),
        sa.Column("interpretation_text", sa.Text(), nullable=False),
        sa.Column("interpretation_type", interpretation_type, nullable=False),
        sa.Column("confirmation_level", confirmation_level, nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["fact_check_runs.id"], name="fact_check_results_run_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "fact_check_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("library_node_id", sa.String(length=100), nullable=True),
        sa.Column("document_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("chunk_label", sa.String(length=255), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("stance", evidence_stance, nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fact_check_evidence_document_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["fact_check_results.id"],
            name="fact_check_evidence_result_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # Drop newly created tables
    op.drop_table("fact_check_evidence")
    op.drop_table("fact_check_results")
    op.drop_table("index_jobs")
    op.drop_table("fact_check_runs")
    with op.batch_alter_table("evidence_seekers") as batch_op:
        batch_op.drop_column("fact_check_publication_mode")
    op.drop_table("evidence_seeker_settings")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS fact_check_evidence_stance")
    op.execute("DROP TYPE IF EXISTS fact_check_confirmation_level")
    op.execute("DROP TYPE IF EXISTS fact_check_interpretation_type")
    op.execute("DROP TYPE IF EXISTS fact_check_run_status")
    op.execute("DROP TYPE IF EXISTS fact_check_run_visibility")
    op.execute("DROP TYPE IF EXISTS fact_check_publication_mode")
    op.execute("DROP TYPE IF EXISTS index_job_status")

    # Remove new column and re-add legacy embedding metadata
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("index_file_key")
        embedding_status_enum = postgresql.ENUM(
            "PENDING", "PROCESSING", "COMPLETED", "FAILED", name="embeddingstatus"
        )
        embedding_status_enum.create(op.get_bind(), checkfirst=True)
        batch_op.add_column(
            sa.Column(
                "embedding_status",
                embedding_status_enum,
                nullable=False,
                server_default="PENDING",
            )
        )
        batch_op.add_column(
            sa.Column("embedding_generated_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("embedding_model", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("embedding_dimensions", sa.Integer(), nullable=True)
        )

    # Re-create embeddings table
    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("document_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding_vector", sa.Text(), nullable=False),
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
            ["document_uuid"], ["documents.uuid"], name="embeddings_document_uuid_fkey"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS embeddings_embedding_vector_idx "
        "ON embeddings USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100)"
    )
