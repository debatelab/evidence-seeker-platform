"""
API endpoints for progress tracking of long-running operations.
"""

import asyncio
import logging
from collections.abc import Callable

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session

from ..core.auth import get_current_user
from ..core.database import get_db
from ..core.progress_tracker import ProgressUpdate, progress_tracker
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/operations/{operation_id}")
def get_operation_status(
    operation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Get the status of a specific operation."""
    status = progress_tracker.get_operation_status(operation_id)
    if not status:
        raise HTTPException(status_code=404, detail="Operation not found")

    # Check if user has access to this operation
    if status["user_id"] != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this operation"
        )

    return status


@router.get("/operations")
def get_user_operations(
    evidence_seeker_uuid: str | None = Query(
        None, description="Filter by evidence seeker"
    ),
    status: list[str] | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Get all operations for the current user."""
    evidence_seeker_id = None
    if evidence_seeker_uuid:
        # Check if user has access to the evidence seeker
        from .evidence_seekers import get_evidence_seeker_by_identifier

        try:
            evidence_seeker = get_evidence_seeker_by_identifier(
                evidence_seeker_uuid, db, int(current_user.id)
            )
            evidence_seeker_id = int(evidence_seeker.id)
        except HTTPException:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access operations for this evidence seeker",
            ) from None

    operations = progress_tracker.get_user_operations(
        user_id=int(current_user.id),
        evidence_seeker_id=evidence_seeker_id,
        status_filter=status,
    )

    return {"operations": operations}


@router.delete("/operations/{operation_id}")
def cancel_operation(
    operation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Cancel a running operation."""
    status = progress_tracker.get_operation_status(operation_id)
    if not status:
        raise HTTPException(status_code=404, detail="Operation not found")

    # Check if user has access to this operation
    if status["user_id"] != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to cancel this operation"
        )

    # Check if operation can be cancelled
    if status["status"] in ["COMPLETED", "FAILED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Operation cannot be cancelled")

    success = progress_tracker.cancel_operation(
        operation_id=operation_id, message="Operation cancelled by user"
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to cancel operation")

    return {"message": "Operation cancelled successfully"}


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for progress updates."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, operation_id: str, websocket: WebSocket) -> None:
        """Connect a WebSocket to an operation."""
        await websocket.accept()

        if operation_id not in self.active_connections:
            self.active_connections[operation_id] = []

        self.active_connections[operation_id].append(websocket)

        # Subscribe to progress updates
        def progress_callback(update: ProgressUpdate) -> None:
            # This will be called from the progress tracker
            # We'll send the update via WebSocket
            asyncio.create_task(self.send_update(operation_id, update))

        progress_tracker.subscribe_to_operation(operation_id, progress_callback)

    def disconnect(self, operation_id: str, websocket: WebSocket) -> None:
        """Disconnect a WebSocket from an operation."""
        if operation_id in self.active_connections:
            if websocket in self.active_connections[operation_id]:
                self.active_connections[operation_id].remove(websocket)

            if not self.active_connections[operation_id]:
                del self.active_connections[operation_id]

    async def send_update(self, operation_id: str, update: ProgressUpdate) -> None:
        """Send a progress update to all connected WebSockets for an operation."""
        if operation_id not in self.active_connections:
            return

        # Prepare the message
        message = {
            "type": "progress_update",
            "operation_id": update.operation_id,
            "progress": update.progress,
            "status": update.status,
            "message": update.message,
            "current_step": update.current_step,
            "total_steps": update.total_steps,
            "estimated_time_remaining": update.estimated_time_remaining,
            "timestamp": update.timestamp.isoformat(),
            "metadata": update.metadata,
        }

        # Send to all connected clients
        disconnected_clients = []
        for websocket in self.active_connections[operation_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {str(e)}")
                disconnected_clients.append(websocket)

        # Clean up disconnected clients
        for client in disconnected_clients:
            self.disconnect(operation_id, client)


# Global WebSocket connection manager
manager = ConnectionManager()


@router.websocket("/ws/operations/{operation_id}")
async def websocket_progress(
    operation_id: str,
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
) -> None:
    """WebSocket endpoint for real-time progress updates."""
    try:
        # Validate token and get user (simplified - in production you'd validate JWT)
        # For now, we'll accept any token and assume user authentication is handled elsewhere
        current_user_id = 1  # This should be extracted from the token

        # Check if operation exists and user has access
        status = progress_tracker.get_operation_status(operation_id)
        if not status:
            await websocket.close(code=404, reason="Operation not found")
            return

        if status["user_id"] != current_user_id:
            await websocket.close(code=403, reason="Not authorized")
            return

        # Connect the WebSocket
        await manager.connect(operation_id, websocket)

        try:
            # Send initial status
            initial_message = {"type": "initial_status", "operation": status}
            await websocket.send_json(initial_message)

            # Keep the connection alive
            while True:
                # Wait for any client messages (ping/pong, etc.)
                # For now, we don't handle client messages
                # In the future, we could handle cancellation requests, etc.
                await websocket.receive_text()

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for operation {operation_id}")
        finally:
            manager.disconnect(operation_id, websocket)

    except Exception as e:
        logger.error(f"WebSocket error for operation {operation_id}: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass


# Integration with embedding service
def create_embedding_progress_callback(
    operation_id: str,
) -> Callable[[ProgressUpdate], None]:
    """Create a progress callback for embedding operations."""

    def callback(update: ProgressUpdate) -> None:
        # This callback will be called by the progress tracker
        # We can add additional logic here if needed
        logger.debug(
            f"Embedding progress update: {update.operation_id} - {update.progress}%"
        )

    return callback


async def track_embedding_generation(
    document_id: int, user_id: int, evidence_seeker_id: int
) -> str:
    """Track the progress of embedding generation for a document."""
    from ..core.database import SessionLocal
    from ..core.embedding_service import embedding_service

    # Start progress tracking
    operation_id = progress_tracker.start_operation(
        operation_type="embedding_generation",
        user_id=user_id,
        evidence_seeker_id=evidence_seeker_id,
        total_steps=1,  # We'll update this as we go
        metadata={"document_id": document_id},
    )

    # Add progress callback
    progress_tracker.subscribe_to_operation(
        operation_id, create_embedding_progress_callback(operation_id)
    )

    try:
        # Update status to running
        progress_tracker.update_progress(
            operation_id=operation_id,
            progress=10.0,
            message="Starting embedding generation",
        )

        # Create database session
        db = SessionLocal()

        try:
            # Generate embeddings
            progress_tracker.update_progress(
                operation_id=operation_id,
                progress=50.0,
                message="Processing document and generating embeddings",
            )

            success = await embedding_service.generate_embeddings_for_document(
                document_id=document_id, db=db
            )

            if success:
                progress_tracker.complete_operation(
                    operation_id=operation_id,
                    message="Embeddings generated successfully",
                )
            else:
                progress_tracker.fail_operation(
                    operation_id=operation_id,
                    error_message="Failed to generate embeddings",
                )

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in embedding generation tracking: {str(e)}")
        progress_tracker.fail_operation(
            operation_id=operation_id, error_message=f"Error: {str(e)}"
        )

    return operation_id
