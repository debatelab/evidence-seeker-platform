"""
Embedding Service for generating document embeddings using LlamaIndex and HuggingFace.

Key change: Avoid heavy model initialization at import time. The embedding model is
now lazily instantiated on first use, preventing test runs (and simple imports) from
attempting to download or load large models which can cause hangs.
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Document, Embedding, EmbeddingStatus

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing document embeddings using LlamaIndex."""

    def __init__(self) -> None:
        self.model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        self.embedding_dimension = 768
        self.chunk_size = 512
        self.chunk_overlap = 50
        # Delay creation of the heavy embedding model until first use to avoid
        # import-time hangs during tests or simple app imports.
        self._embedding_model: Any | None = None

        logger.info("Initialized EmbeddingService (lazy model: %s)", self.model_name)

    def _ensure_model(self) -> None:
        """Lazily initialize the embedding model when first needed.

        Heavy imports are kept inside this method to avoid import-time side effects.
        """
        if settings.disable_embeddings:
            # In disabled mode, do not load any heavy dependency.
            logger.info("Embedding model loading skipped (disable_embeddings=True)")
            return

        if self._embedding_model is not None:
            return

        # Import heavy deps only when needed
        from llama_index.embeddings.huggingface import (
            HuggingFaceEmbedding,  # type: ignore[import-untyped]
        )

        self._embedding_model = HuggingFaceEmbedding(
            model_name=self.model_name, embed_batch_size=10, trust_remote_code=True
        )
        logger.info("Embedding model loaded: %s", self.model_name)

    async def generate_embeddings_for_document(
        self, document_id: int, db: Session
    ) -> bool:
        """
        Generate embeddings for a document using LlamaIndex workflow.

        Args:
            document_id: ID of the document to process
            db: Database session

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get document from database
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document {document_id} not found")
                return False

            # Update status to processing
            document.embedding_status = EmbeddingStatus.PROCESSING  # type: ignore[assignment]
            db.commit()

            start_time = time.time()

            # If embeddings are disabled (tests/CI), short-circuit with SUCCESS
            if settings.disable_embeddings:
                logger.info(
                    "Embeddings disabled via settings. Marking document %s as COMPLETED (stub).",
                    document_id,
                )
                document.embedding_status = EmbeddingStatus.COMPLETED  # type: ignore[assignment]
                document.embedding_generated_at = datetime.utcnow()  # type: ignore[assignment]
                document.embedding_model = "disabled"
                document.embedding_dimensions = 0  # type: ignore[assignment]
                db.commit()
                return True

            # Load document using LlamaIndex SimpleDirectoryReader
            file_path = Path(document.file_path)
            if not file_path.exists():
                logger.error(f"Document file not found: {file_path}")
                document.embedding_status = EmbeddingStatus.FAILED  # type: ignore[assignment]
                db.commit()
                return False

            # Create a temporary directory with the single file
            # Import here to avoid heavy module import on service import
            from llama_index.core import (
                SimpleDirectoryReader,  # type: ignore[import-untyped]
            )

            reader = SimpleDirectoryReader(
                input_files=[str(file_path)], recursive=False
            )

            # Load documents
            llama_documents = reader.load_data()

            if not llama_documents:
                logger.error(f"No content loaded from document {document_id}")
                document.embedding_status = EmbeddingStatus.FAILED  # type: ignore[assignment]
                db.commit()
                return False

            # Process each document chunk
            total_chunks = len(llama_documents)
            embeddings_created = 0

            for idx, llama_doc in enumerate(llama_documents):
                try:
                    # Generate embedding for this chunk
                    chunk_text = llama_doc.text
                    if not chunk_text.strip():
                        continue

                    # Ensure model is available and get embedding vector
                    self._ensure_model()
                    if settings.disable_embeddings:
                        # Provide a tiny deterministic stub embedding to satisfy DB types
                        embedding_vector = [0.0] * 3  # minimal placeholder
                    else:
                        embedding_vector = self._embedding_model.get_text_embedding(chunk_text)  # type: ignore[union-attr]

                    # Create embedding record
                    embedding = Embedding(
                        document_id=document_id,
                        document_uuid=document.uuid,
                        embedding_vector=embedding_vector,
                        model_name=self.model_name,
                        chunk_text=chunk_text[:1000],  # Store first 1000 chars
                        chunk_index=idx,
                        total_chunks=total_chunks,
                        processing_time_ms=int(
                            (time.time() - start_time) * 1000 / (idx + 1)
                        ),
                    )

                    db.add(embedding)
                    embeddings_created += 1

                except Exception as e:
                    logger.error(
                        f"Error processing chunk {idx} for document {document_id}: {str(e)}"
                    )
                    continue

            # Update document status
            if embeddings_created > 0:
                document.embedding_status = EmbeddingStatus.COMPLETED  # type: ignore[assignment]
                document.embedding_generated_at = datetime.utcnow()  # type: ignore[assignment]
                document.embedding_model = self.model_name  # type: ignore[assignment]
                document.embedding_dimensions = self.embedding_dimension  # type: ignore[assignment]
                logger.info(
                    f"Successfully generated {embeddings_created} embeddings for document {document_id}"
                )
            else:
                document.embedding_status = EmbeddingStatus.FAILED  # type: ignore[assignment]
                logger.error(f"No embeddings generated for document {document_id}")

            db.commit()
            return embeddings_created > 0

        except Exception as e:
            logger.error(
                f"Error generating embeddings for document {document_id}: {str(e)}"
            )
            try:
                if document:
                    document.embedding_status = EmbeddingStatus.FAILED  # type: ignore[assignment]
                    db.commit()
            except Exception:
                pass
            return False

    def generate_embeddings_batch(
        self, document_ids: list[int], db: Session
    ) -> dict[int, bool]:
        """
        Generate embeddings for multiple documents sequentially.

        Args:
            document_ids: List of document IDs to process
            db: Database session

        Returns:
            Dict mapping document IDs to success status
        """
        results = {}

        for doc_id in document_ids:
            try:
                # Note: This is synchronous processing for now
                # In a production environment, you might want to use asyncio.to_thread()
                # or a proper async implementation
                success = asyncio.run(self.generate_embeddings_for_document(doc_id, db))
                results[doc_id] = success
            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {str(e)}")
                results[doc_id] = False

        return results

    def get_text_embedding(self, text: str) -> list[float]:
        """Return an embedding for the given text or a stub when disabled.

        This avoids accessing internal model attributes from other modules and
        centralizes the disable_embeddings logic.
        """
        if settings.disable_embeddings:
            # Return small deterministic stub to keep downstream code simple
            return [0.0, 0.0, 0.0]
        self._ensure_model()
        # type: ignore[union-attr]
        return self._embedding_model.get_text_embedding(text)

    def get_embedding_model_info(self) -> dict[str, Any]:
        """Get information about the current embedding model."""
        batch_size: int | None = None
        if self._embedding_model is not None:
            try:
                # type: ignore[attr-defined]
                batch_size = int(self._embedding_model.embed_batch_size)  # type: ignore[assignment]
            except Exception:
                batch_size = None

        return {
            "model_name": self.model_name,
            "dimensions": self.embedding_dimension,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embed_batch_size": batch_size,
        }

    async def get_document_embedding_status(
        self, document_id: int, db: Session
    ) -> dict[str, Any] | None:
        """
        Get the embedding status and statistics for a document.

        Args:
            document_id: ID of the document

        Returns:
            Dict with status information or None if document not found
        """
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return None

        # Count embeddings for this document
        embedding_count = (
            db.query(Embedding).filter(Embedding.document_id == document_id).count()
        )

        return {
            "document_id": document_id,
            "status": document.embedding_status.value,
            "embedding_count": embedding_count,
            "model": document.embedding_model,
            "dimensions": document.embedding_dimensions,
            "generated_at": (
                document.embedding_generated_at.isoformat()
                if document.embedding_generated_at
                else None
            ),
        }


# Global instance
embedding_service = EmbeddingService()
