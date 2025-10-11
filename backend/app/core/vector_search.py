"""
Vector Search Service for similarity search using PostgreSQL + pgvector.

Important: Avoid importing heavy libraries (llama-index) at module import time.
This module uses raw SQL with pgvector operators and relies on the embedding
service to generate query embeddings. When embeddings are disabled (e.g., tests),
the search methods short-circuit to fast, empty responses to prevent hangs.
"""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db_connection_string
from app.core.embedding_service import embedding_service
from app.models import Document, Embedding

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Service for performing vector similarity search using PGVectorStore."""

    def __init__(self) -> None:
        self.connection_string = get_db_connection_string()
        self.table_name = "embeddings"
        logger.info("Initialized VectorSearchService (no heavy imports)")

    def search_similar(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.1,
        document_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar documents using vector similarity.

        Args:
            query: Search query text
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            document_ids: Optional list of document IDs to search within

        Returns:
            List of search results with similarity scores
        """
        try:
            # Short-circuit when embeddings are disabled (tests/CI)
            if settings.disable_embeddings:
                logger.info("Vector search skipped (disable_embeddings=True)")
                return []

            # Generate embedding for the query
            query_embedding = embedding_service.get_text_embedding(query)

            # Build the search query
            search_query = f"""
            SELECT
                e.id,
                e.document_id,
                e.chunk_text,
                e.chunk_index,
                e.model_name,
                1 - (e.embedding_vector <=> '{query_embedding}') as similarity
            FROM embeddings e
            WHERE 1 - (e.embedding_vector <=> '{query_embedding}') > {similarity_threshold}
            """

            # Add document filter if specified
            if document_ids:
                doc_ids_str = ",".join(map(str, document_ids))
                search_query += f" AND e.document_id IN ({doc_ids_str})"

            # Add ordering and limit
            search_query += f"""
            ORDER BY e.embedding_vector <=> '{query_embedding}'
            LIMIT {limit}
            """

            # Execute the search
            results = self._execute_raw_query(search_query)

            # Format results
            formatted_results = []
            for row in results:
                formatted_results.append(
                    {
                        "embedding_id": row["id"],
                        "document_id": row["document_id"],
                        "chunk_text": row["chunk_text"],
                        "chunk_index": row["chunk_index"],
                        "model_name": row["model_name"],
                        "similarity_score": float(row["similarity"]),
                    }
                )

            logger.info(
                f"Vector search completed. Found {len(formatted_results)} results for query: {query[:50]}..."
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Error performing vector search: {str(e)}")
            return []

    def search_by_embedding(
        self,
        query_embedding: list[float],
        limit: int = 10,
        similarity_threshold: float = 0.1,
        document_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search using a pre-computed embedding vector.

        Args:
            query_embedding: Pre-computed embedding vector
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            document_ids: Optional list of document IDs to search within

        Returns:
            List of search results with similarity scores
        """
        try:
            if settings.disable_embeddings:
                logger.info(
                    "Vector search by embedding skipped (disable_embeddings=True)"
                )
                return []
            # Convert embedding to PostgreSQL vector format
            embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

            # Build the search query
            search_query = f"""
            SELECT
                e.id,
                e.document_id,
                e.chunk_text,
                e.chunk_index,
                e.model_name,
                1 - (e.embedding_vector <=> '{embedding_str}') as similarity
            FROM embeddings e
            WHERE 1 - (e.embedding_vector <=> '{embedding_str}') > {similarity_threshold}
            """

            # Add document filter if specified
            if document_ids:
                doc_ids_str = ",".join(map(str, document_ids))
                search_query += f" AND e.document_id IN ({doc_ids_str})"

            # Add ordering and limit
            search_query += f"""
            ORDER BY e.embedding_vector <=> '{embedding_str}'
            LIMIT {limit}
            """

            # Execute the search
            results = self._execute_raw_query(search_query)

            # Format results
            formatted_results = []
            for row in results:
                formatted_results.append(
                    {
                        "embedding_id": row["id"],
                        "document_id": row["document_id"],
                        "chunk_text": row["chunk_text"],
                        "chunk_index": row["chunk_index"],
                        "model_name": row["model_name"],
                        "similarity_score": float(row["similarity"]),
                    }
                )

            logger.info(
                f"Vector search by embedding completed. Found {len(formatted_results)} results"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Error performing vector search by embedding: {str(e)}")
            return []

    def get_document_chunks(
        self, document_id: int, db: Session
    ) -> list[dict[str, Any]]:
        """
        Get all embedding chunks for a specific document.

        Args:
            document_id: ID of the document
            db: Database session

        Returns:
            List of document chunks with their embeddings
        """
        try:
            embeddings = (
                db.query(Embedding)
                .filter(Embedding.document_id == document_id)
                .order_by(Embedding.chunk_index)
                .all()
            )

            results = []
            for embedding in embeddings:
                results.append(
                    {
                        "id": embedding.id,
                        "chunk_index": embedding.chunk_index,
                        "chunk_text": embedding.chunk_text,
                        "total_chunks": embedding.total_chunks,
                        "processing_time_ms": embedding.processing_time_ms,
                        "created_at": embedding.created_at.isoformat(),
                    }
                )

            return results

        except Exception as e:
            logger.error(
                f"Error getting document chunks for document {document_id}: {str(e)}"
            )
            return []

    def get_search_statistics(self, db: Session) -> dict[str, Any]:
        """
        Get statistics about the vector search index.

        Args:
            db: Database session

        Returns:
            Dictionary with search statistics
        """
        try:
            # Count total embeddings
            total_embeddings = db.query(Embedding).count()

            # Count total documents with embeddings
            documents_with_embeddings = (
                db.query(Document)
                .filter(Document.embedding_status == "COMPLETED")
                .count()
            )

            # Get embedding model statistics
            model_stats = db.execute(
                text(
                    """
                SELECT model_name, COUNT(*) as count
                FROM embeddings
                GROUP BY model_name
            """
                )
            ).fetchall()

            return {
                "total_embeddings": total_embeddings,
                "documents_with_embeddings": documents_with_embeddings,
                "embedding_models": [
                    {"model": row[0], "count": row[1]} for row in model_stats
                ],
                "vector_dimensions": 768,
            }

        except Exception as e:
            logger.error(f"Error getting search statistics: {str(e)}")
            return {
                "total_embeddings": 0,
                "documents_with_embeddings": 0,
                "embedding_models": [],
                "vector_dimensions": 768,
            }

    def _execute_raw_query(self, query: str) -> list[dict[str, Any]]:
        """
        Execute a raw SQL query and return results.

        Args:
            query: SQL query to execute

        Returns:
            List of result dictionaries
        """
        try:
            # Get database connection
            from app.core.database import engine

            with engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()

                # Convert to dictionaries
                results = []
                for row in rows:
                    results.append(dict(row._mapping))

                return results

        except Exception as e:
            logger.error(f"Error executing raw query: {str(e)}")
            return []


# Global instance
vector_search_service = VectorSearchService()
