from uuid import uuid4

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Embedding(Base):
    """Document embedding SQLAlchemy model with pgvector support"""

    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid4)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    document_uuid = Column(
        UUID(as_uuid=True), ForeignKey("documents.uuid"), nullable=False
    )

    # Embedding vector (768 dimensions for paraphrase-multilingual-mpnet-base-v2)
    embedding_vector = Column(Vector(768), nullable=False)

    # Metadata
    model_name = Column(
        String(100), nullable=False
    )  # e.g., "paraphrase-multilingual-mpnet-base-v2"
    chunk_text = Column(Text, nullable=True)  # Original text chunk that was embedded
    chunk_index = Column(Integer, nullable=False)  # Index of chunk within document
    total_chunks = Column(
        Integer, nullable=False
    )  # Total number of chunks for this document

    # Processing metadata
    processing_time_ms = Column(
        Integer, nullable=True
    )  # Time taken to generate embedding
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    document = relationship(
        "Document", backref="embeddings", foreign_keys=[document_id]
    )

    def __repr__(self) -> str:
        return f"<Embedding(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"

    @property
    def dimensions(self) -> int:
        """Get the dimensions of the embedding vector"""
        return len(self.embedding_vector) if self.embedding_vector else 0


# Create vector similarity search index
Index(
    "embeddings_embedding_vector_idx",
    Embedding.embedding_vector,
    postgresql_using="ivfflat",
    postgresql_with={"lists": 100},
    postgresql_ops={"embedding_vector": "vector_cosine_ops"},
)
