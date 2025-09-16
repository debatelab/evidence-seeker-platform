"""
API endpoints for vector search operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from ..core.database import get_db
from ..core.vector_search import vector_search_service
from ..core.auth import get_current_user
from ..models import Document


router = APIRouter()


class SearchRequest(BaseModel):
    """Request model for vector search"""

    query: str
    limit: Optional[int] = 10
    similarity_threshold: Optional[float] = 0.1
    document_ids: Optional[List[int]] = None


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
    results: List[SearchResult]
    total_results: int


class SearchStatistics(BaseModel):
    """Response model for search statistics"""

    total_embeddings: int
    documents_with_embeddings: int
    embedding_models: List[Dict[str, Any]]
    vector_dimensions: int


@router.post("/", response_model=SearchResponse)
def search_documents(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
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
                    get_evidence_seeker_by_identifier(
                        document.evidence_seeker_uuid, db, current_user.id
                    )
                except HTTPException:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Not authorized to search document {doc_id}",
                    )

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
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/statistics", response_model=SearchStatistics)
def get_search_statistics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get statistics about the vector search index"""
    try:
        stats = vector_search_service.get_search_statistics(db)
        return SearchStatistics(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/document-chunks/{document_id}")
def get_document_chunks(
    document_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all embedding chunks for a specific document"""
    # Check if document exists and user has access
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check access to evidence_seeker
    from .evidence_seekers import get_evidence_seeker_by_identifier

    try:
        get_evidence_seeker_by_identifier(
            document.evidence_seeker_uuid, db, current_user.id
        )
    except HTTPException:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this document"
        )

    try:
        chunks = vector_search_service.get_document_chunks(document_id, db)
        return {"document_id": document_id, "chunks": chunks}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get document chunks: {str(e)}"
        )


@router.post("/by-embedding")
def search_by_embedding(
    query_embedding: List[float],
    limit: Optional[int] = 10,
    similarity_threshold: Optional[float] = 0.1,
    document_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
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
                        document.evidence_seeker_uuid, db, current_user.id
                    )
                except HTTPException:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Not authorized to search document {doc_id}",
                    )

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
        )


@router.get("/similar-documents/{document_id}")
def find_similar_documents(
    document_id: int,
    limit: Optional[int] = 5,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Find documents similar to the given document"""
    # Check if document exists and user has access
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check access to evidence_seeker
    from .evidence_seekers import get_evidence_seeker_by_identifier

    try:
        get_evidence_seeker_by_identifier(
            document.evidence_seeker_uuid, db, current_user.id
        )
    except HTTPException:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this document"
        )

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
        )
