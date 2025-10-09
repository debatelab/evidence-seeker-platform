"""
API endpoints for embedding operations.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.auth import get_current_user
from ..core.database import get_db
from ..core.embedding_service import embedding_service
from ..models import Document
from ..models.user import User

router = APIRouter()


class EmbeddingStatusResponse(BaseModel):
    """Response model for embedding status"""

    document_id: int
    status: str
    embedding_count: int
    model: str | None
    dimensions: int | None
    generated_at: str | None


class EmbeddingRegenerateRequest(BaseModel):
    """Request model for regenerating embeddings"""

    document_id: int


@router.get("/status/{document_id}", response_model=EmbeddingStatusResponse)
async def get_embedding_status(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmbeddingStatusResponse:
    """Get the embedding status for a specific document"""
    # Check if document exists and user has access
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if user has access to the evidence_seeker
    from .evidence_seekers import get_evidence_seeker_by_identifier

    try:
        # Use string form of UUID to satisfy typing
        evidence_seeker_identifier: str = str(document.evidence_seeker_uuid)
        get_evidence_seeker_by_identifier(
            evidence_seeker_identifier, db, int(current_user.id)
        )
    except HTTPException:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this document"
        ) from None

    # Get embedding status
    status_info = await embedding_service.get_document_embedding_status(document_id, db)
    if not status_info:
        raise HTTPException(status_code=404, detail="Document not found")

    return EmbeddingStatusResponse(**status_info)


@router.post("/regenerate")
async def regenerate_embeddings(
    request: EmbeddingRegenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Regenerate embeddings for a specific document"""
    # Check if document exists and user has access
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if user has access to the evidence_seeker
    from .evidence_seekers import get_evidence_seeker_by_identifier

    try:
        get_evidence_seeker_by_identifier(
            str(document.evidence_seeker_uuid), db, int(current_user.id)
        )
    except HTTPException:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this document"
        ) from None

    # Trigger embedding regeneration
    # Note: In a real implementation, you'd want to use BackgroundTasks here.
    # For now, we await directly for simplicity.
    try:
        success = await embedding_service.generate_embeddings_for_document(
            request.document_id, db
        )
        if success:
            return {"message": "Embeddings regenerated successfully"}
        else:
            raise HTTPException(
                status_code=500, detail="Failed to regenerate embeddings"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error regenerating embeddings: {str(e)}"
        ) from None


@router.get("/model-info")
def get_embedding_model_info() -> dict[str, Any]:
    """Get information about the current embedding model"""
    return embedding_service.get_embedding_model_info()


@router.get("/batch-status")
async def get_batch_embedding_status(
    document_ids: list[int] = Query(..., description="List of document IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, list[dict[str, object]]]:
    """Get embedding status for multiple documents"""
    results = []

    for doc_id in document_ids:
        try:
            # Check if document exists and user has access
            document = db.query(Document).filter(Document.id == doc_id).first()
            if not document:
                results.append({"document_id": doc_id, "error": "Document not found"})
                continue

            # Check access
            from .evidence_seekers import get_evidence_seeker_by_identifier

            try:
                # Extract identifier as string to satisfy typing
                evidence_seeker_identifier: str = str(document.evidence_seeker_uuid)
                get_evidence_seeker_by_identifier(
                    evidence_seeker_identifier, db, int(current_user.id)
                )
            except HTTPException:
                results.append({"document_id": doc_id, "error": "Not authorized"})
                continue

            # Get status
            status_info = await embedding_service.get_document_embedding_status(
                doc_id, db
            )
            if status_info:
                results.append(status_info)
            else:
                results.append({"document_id": doc_id, "error": "Status not available"})

        except Exception as e:
            results.append({"document_id": doc_id, "error": str(e)})

    return {"results": results}
