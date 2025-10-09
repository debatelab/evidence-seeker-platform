"""
Pydantic schemas for vector search and analysis operations.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Schema for search query input."""

    query: str = Field(..., description="The search query text")
    limit: int | None = Field(10, description="Maximum number of results to return")
    similarity_threshold: float | None = Field(
        0.1, description="Minimum similarity score (0.0 to 1.0)"
    )
    document_ids: list[int] | None = Field(
        None, description="Optional list of document IDs to search within"
    )


class SearchResult(BaseModel):
    """Schema for individual search result."""

    embedding_id: int = Field(..., description="ID of the embedding")
    document_id: int = Field(..., description="ID of the document")
    chunk_text: str = Field(..., description="Text content of the matched chunk")
    chunk_index: int = Field(..., description="Index of the chunk within the document")
    model_name: str = Field(..., description="Name of the embedding model used")
    similarity_score: float = Field(..., description="Similarity score (0.0 to 1.0)")


class SearchResponse(BaseModel):
    """Schema for search operation response."""

    query: str = Field(..., description="The original search query")
    results: list[SearchResult] = Field(..., description="List of search results")
    total_results: int = Field(..., description="Total number of results returned")


class EmbeddingSearchQuery(BaseModel):
    """Schema for embedding-based search query."""

    embedding: list[float] = Field(..., description="Pre-computed embedding vector")
    limit: int | None = Field(10, description="Maximum number of results to return")
    similarity_threshold: float | None = Field(
        0.1, description="Minimum similarity score (0.0 to 1.0)"
    )
    document_ids: list[int] | None = Field(
        None, description="Optional list of document IDs to search within"
    )


class EmbeddingSearchResponse(BaseModel):
    """Schema for embedding search response."""

    query_embedding_dimensions: int = Field(
        ..., description="Dimensions of the query embedding"
    )
    results: list[SearchResult] = Field(..., description="List of search results")
    total_results: int = Field(..., description="Total number of results returned")


class DocumentChunk(BaseModel):
    """Schema for document chunk information."""

    id: int = Field(..., description="Embedding ID")
    chunk_index: int = Field(..., description="Index of the chunk within the document")
    chunk_text: str = Field(..., description="Text content of the chunk")
    total_chunks: int = Field(..., description="Total number of chunks in the document")
    processing_time_ms: int | None = Field(
        None, description="Time taken to process this chunk"
    )
    created_at: datetime = Field(..., description="When the embedding was created")


class DocumentChunksResponse(BaseModel):
    """Schema for document chunks response."""

    document_id: int = Field(..., description="ID of the document")
    chunks: list[DocumentChunk] = Field(..., description="List of document chunks")


class SearchStatistics(BaseModel):
    """Schema for search statistics."""

    total_embeddings: int = Field(
        ..., description="Total number of embeddings in the system"
    )
    documents_with_embeddings: int = Field(
        ..., description="Number of documents that have embeddings"
    )
    embedding_models: list[dict[str, Any]] = Field(
        ..., description="List of embedding models and their usage counts"
    )
    vector_dimensions: int = Field(
        ..., description="Dimensions of the embedding vectors"
    )


class SimilarDocumentsQuery(BaseModel):
    """Schema for similar documents query."""

    limit: int | None = Field(
        5, description="Maximum number of similar documents to return"
    )


class SimilarDocumentsResponse(BaseModel):
    """Schema for similar documents response."""

    document_id: int = Field(..., description="ID of the original document")
    query_chunk: str = Field(..., description="Text chunk used for similarity search")
    similar_documents: list[SearchResult] = Field(
        ..., description="List of similar documents"
    )


class AnalysisQuery(BaseModel):
    """Schema for statement analysis query."""

    statement: str = Field(..., description="The statement to analyze")
    context_document_ids: list[int] | None = Field(
        None, description="Optional list of document IDs to use as context"
    )
    max_context_chunks: int | None = Field(
        10, description="Maximum number of context chunks to consider"
    )


class AnalysisResult(BaseModel):
    """Schema for analysis result."""

    statement: str = Field(..., description="The original statement")
    analysis: str = Field(..., description="Analysis result (placeholder for now)")
    confidence_score: float = Field(..., description="Confidence score of the analysis")
    supporting_evidence: list[SearchResult] = Field(
        ..., description="Supporting evidence from documents"
    )
    context_used: int = Field(..., description="Number of context chunks used")


class ProgressUpdate(BaseModel):
    """Schema for progress updates during long-running operations."""

    operation_id: str = Field(..., description="Unique identifier for the operation")
    progress: float = Field(..., description="Progress percentage (0.0 to 100.0)")
    status: str = Field(..., description="Current status message")
    current_step: int | None = Field(None, description="Current step number")
    total_steps: int | None = Field(None, description="Total number of steps")
    estimated_time_remaining: int | None = Field(
        None, description="Estimated time remaining in seconds"
    )


class BatchOperationStatus(BaseModel):
    """Schema for batch operation status."""

    operation_id: str = Field(
        ..., description="Unique identifier for the batch operation"
    )
    total_items: int = Field(..., description="Total number of items to process")
    processed_items: int = Field(..., description="Number of items processed so far")
    successful_items: int = Field(
        ..., description="Number of successfully processed items"
    )
    failed_items: int = Field(..., description="Number of failed items")
    status: str = Field(..., description="Overall status of the batch operation")
    created_at: datetime = Field(..., description="When the operation was started")
    updated_at: datetime = Field(..., description="When the operation was last updated")
