"""
Embedding Service for generating document embeddings using LlamaIndex and HuggingFace.
"""

import asyncio
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from llama_index.core import SimpleDirectoryReader, Document as LlamaDocument
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Document, Embedding, EmbeddingStatus
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing document embeddings using LlamaIndex."""

    def __init__(self):
        self.model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        self.embedding_dimension = 768
        self.chunk_size = 512
        self.chunk_overlap = 50

        # Initialize embedding model
        self.embedding_model = HuggingFaceEmbedding(
            model_name=self.model_name, embed_batch_size=10, trust_remote_code=True
        )

        logger.info(f"Initialized EmbeddingService with model: {self.model_name}")

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
            document.embedding_status = EmbeddingStatus.PROCESSING
            db.commit()

            start_time = time.time()

            # Load document using LlamaIndex SimpleDirectoryReader
            file_path = Path(document.file_path)
            if not file_path.exists():
                logger.error(f"Document file not found: {file_path}")
                document.embedding_status = EmbeddingStatus.FAILED
                db.commit()
                return False

            # Create a temporary directory with the single file
            temp_dir = file_path.parent
            reader = SimpleDirectoryReader(
                input_files=[str(file_path)], recursive=False
            )

            # Load documents
            llama_documents = reader.load_data()

            if not llama_documents:
                logger.error(f"No content loaded from document {document_id}")
                document.embedding_status = EmbeddingStatus.FAILED
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

                    # Get embedding vector
                    embedding_vector = self.embedding_model.get_text_embedding(
                        chunk_text
                    )

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
                document.embedding_status = EmbeddingStatus.COMPLETED
                document.embedding_generated_at = datetime.utcnow()
                document.embedding_model = self.model_name
                document.embedding_dimensions = self.embedding_dimension
                logger.info(
                    f"Successfully generated {embeddings_created} embeddings for document {document_id}"
                )
            else:
                document.embedding_status = EmbeddingStatus.FAILED
                logger.error(f"No embeddings generated for document {document_id}")

            db.commit()
            return embeddings_created > 0

        except Exception as e:
            logger.error(
                f"Error generating embeddings for document {document_id}: {str(e)}"
            )
            try:
                document.embedding_status = EmbeddingStatus.FAILED
                db.commit()
            except:
                pass
            return False

    def generate_embeddings_batch(
        self, document_ids: List[int], db: Session
    ) -> Dict[int, bool]:
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

    def get_embedding_model_info(self) -> Dict[str, Any]:
        """Get information about the current embedding model."""
        return {
            "model_name": self.model_name,
            "dimensions": self.embedding_dimension,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embed_batch_size": self.embedding_model.embed_batch_size,
        }

    async def get_document_embedding_status(
        self, document_id: int, db: Session
    ) -> Optional[Dict[str, Any]]:
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
