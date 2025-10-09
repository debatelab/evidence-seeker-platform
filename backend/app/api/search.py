"""
API endpoints for vector search operations.
"""

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.auth import get_current_user
from ..core.database import get_db
from ..core.vector_search import vector_search_service
from ..models import Document, User

router = APIRouter()


class SearchRequest(BaseModel):
    """Request model for vector search"""

    query: str
    limit: int | None = 10
    similarity_threshold: float | None = 0.1
    document_ids: list[int] | None = None


class SearchResult(BaseModel):
    """Response model for search results"""

    embedding_id: int
    document_id: int
    chunk_text: str
    chunk_index: int
    model_name: str
    similarity_score: float


class SearchResponse(BaseModel):
    """Response model for search operation"""

    query: str
    results: list[SearchResult]
    total_results: int


class SearchStatistics(BaseModel):
    """Response model for search statistics"""

    total_embeddings: int
    documents_with_embeddings: int
    embedding_models: list[dict[str, Any]]
    vector_dimensions: int


@router.post("/", response_model=SearchResponse)
def search_documents(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    """Perform vector search across documents"""
    try:
        # If document_ids are specified, check user access
        if request.document_ids:
            for doc_id in request.document_ids:
                document = db.query(Document).filter(Document.id == doc_id).first()
                if not document:
                    raise HTTPException(
                        status_code=404, detail=f"Document {doc_id} not found"
                    )

                # Check access to evidence_seeker
                from .evidence_seekers import get_evidence_seeker_by_identifier

                try:
                    # Extract scalar UUID value from document model
                    evidence_seeker_uuid = document.evidence_seeker_uuid
                    get_evidence_seeker_by_identifier(
                        str(evidence_seeker_uuid), db, int(current_user.id)
                    )
                except HTTPException:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Not authorized to search document {doc_id}",
                    ) from None

        # Perform the search
        results = vector_search_service.search_similar(
            query=request.query,
            limit=request.limit or 10,
            similarity_threshold=request.similarity_threshold or 0.1,
            document_ids=request.document_ids,
        )

        # Convert to response format
        search_results = [SearchResult(**result) for result in results]

        return SearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Search failed: {str(e)}"
        ) from None


@router.get("/statistics", response_model=SearchStatistics)
def get_search_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchStatistics:
    """Get statistics about the vector search index"""
    try:
        stats = vector_search_service.get_search_statistics(db)
        return SearchStatistics(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get statistics: {str(e)}"
        ) from None


@router.get("/document-chunks/{document_id}")
def get_document_chunks(
    document_id: int = Path(..., description="The document ID to get chunks for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get all embedding chunks for a specific document"""
    # Check if document exists and user has access
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check access to evidence_seeker
    from .evidence_seekers import get_evidence_seeker_by_identifier

    try:
        # Extract scalar UUID value from document model
        evidence_seeker_uuid = document.evidence_seeker_uuid
        get_evidence_seeker_by_identifier(
            str(evidence_seeker_uuid), db, int(current_user.id)
        )
    except HTTPException:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this document"
        ) from None

    try:
        chunks = vector_search_service.get_document_chunks(document_id, db)
        return {"document_id": document_id, "chunks": chunks}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get document chunks: {str(e)}"
        ) from None


@router.post("/by-embedding")
def search_by_embedding(
    query_embedding: list[float] = Body(
        ..., description="The embedding vector to search with"
    ),
    limit: int | None = Query(10, description="Maximum number of results to return"),
    similarity_threshold: float | None = Query(
        0.1, description="Similarity threshold for results"
    ),
    document_ids: list[int] | None = Query(
        None, description="Specific document IDs to search within"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Search using a pre-computed embedding vector"""
    try:
        # If document_ids are specified, check user access
        if document_ids:
            for doc_id in document_ids:
                document = db.query(Document).filter(Document.id == doc_id).first()
                if not document:
                    raise HTTPException(
                        status_code=404, detail=f"Document {doc_id} not found"
                    )

                # Check access to evidence_seeker
                from .evidence_seekers import get_evidence_seeker_by_identifier

                try:
                    get_evidence_seeker_by_identifier(
                        str(document.evidence_seeker_uuid), db, int(current_user.id)
                    )
                except HTTPException:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Not authorized to search document {doc_id}",
                    ) from None

        # Perform the search
        results = vector_search_service.search_by_embedding(
            query_embedding=query_embedding,
            limit=limit or 10,
            similarity_threshold=similarity_threshold or 0.1,
            document_ids=document_ids,
        )

        return {
            "query_embedding_dimensions": len(query_embedding),
            "results": results,
            "total_results": len(results),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Embedding search failed: {str(e)}"
        ) from None


@router.get("/similar-documents/{document_id}")
def find_similar_documents(
    document_id: int = Path(
        ..., description="The document ID to find similar documents for"
    ),
    limit: int | None = Query(
        5, description="Maximum number of similar documents to return"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Find documents similar to the given document"""
    # Check if document exists and user has access
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check access to evidence_seeker
    from .evidence_seekers import get_evidence_seeker_by_identifier

    try:
        # Extract scalar UUID value from document model
        evidence_seeker_uuid = document.evidence_seeker_uuid
        # Ensure we pass a concrete int for current_user_id
        get_evidence_seeker_by_identifier(
            str(evidence_seeker_uuid), db, int(current_user.id)
        )
    except HTTPException:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this document"
        ) from None

    try:
        # Get embeddings for this document
        embeddings = vector_search_service.get_document_chunks(document_id, db)

        if not embeddings:
            return {
                "document_id": document_id,
                "message": "No embeddings found for this document",
                "similar_documents": [],
            }

        # Use the first embedding as query (simplified approach)
        # In a real implementation, you might want to average all embeddings
        first_chunk = embeddings[0]
        if "embedding_vector" in first_chunk:
            # If we had the actual embedding vector, we could use it
            # For now, we'll use the chunk text
            query_text = first_chunk.get("chunk_text", "")
            if query_text:
                # Search for similar content, excluding the current document
                results = vector_search_service.search_similar(
                    query=query_text,
                    limit=(limit or 5) + 1,  # +1 to account for self-match
                    similarity_threshold=0.1,
                )

                # Filter out results from the same document
                similar_results = [
                    result for result in results if result["document_id"] != document_id
                ][: limit or 5]

                return {
                    "document_id": document_id,
                    "query_chunk": (
                        query_text[:100] + "..."
                        if len(query_text) > 100
                        else query_text
                    ),
                    "similar_documents": similar_results,
                }

        return {
            "document_id": document_id,
            "message": "Could not find similar documents",
            "similar_documents": [],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to find similar documents: {str(e)}"
        ) from None
