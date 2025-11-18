"""
Progress tracking service for long-running AI operations.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class OperationStatus(Enum):
    """Status of a long-running operation."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ProgressUpdate:
    """Represents a progress update for an operation."""

    operation_id: str
    progress: float  # 0.0 to 100.0
    status: str
    message: str
    current_step: int | None = None
    total_steps: int | None = None
    estimated_time_remaining: int | None = None  # seconds
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationInfo:
    """Information about a long-running operation."""

    operation_id: str
    operation_type: str  # e.g., "embedding_generation", "batch_search"
    status: OperationStatus
    progress: float
    message: str
    created_at: datetime
    updated_at: datetime
    user_id: int
    evidence_seeker_id: int | None = None
    current_step: int | None = None
    total_steps: int | None = None
    estimated_time_remaining: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    callbacks: list[Callable] = field(default_factory=list)


@dataclass
class TrackerEvent:
    """Simple analytics event captured during onboarding."""

    name: str
    user_id: int | None
    evidence_seeker_id: int | None
    metadata: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ProgressTracker:
    """Service for tracking progress of long-running operations."""

    def __init__(self) -> None:
        self.operations: dict[str, OperationInfo] = {}
        self.subscribers: dict[str, list[Callable]] = {}
        self._cleanup_task: asyncio.Task | None = None
        self.events: list[TrackerEvent] = []

    def start_operation(
        self,
        operation_type: str,
        user_id: int,
        evidence_seeker_id: int | None = None,
        total_steps: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Start tracking a new operation."""
        operation_id = str(uuid.uuid4())

        operation = OperationInfo(
            operation_id=operation_id,
            operation_type=operation_type,
            status=OperationStatus.PENDING,
            progress=0.0,
            message="Operation started",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            user_id=user_id,
            evidence_seeker_id=evidence_seeker_id,
            total_steps=total_steps,
            metadata=metadata or {},
        )

        self.operations[operation_id] = operation

        logger.info(
            f"Started operation {operation_id} of type {operation_type} for user {user_id}"
        )
        return operation_id

    def update_progress(
        self,
        operation_id: str,
        progress: float,
        message: str,
        current_step: int | None = None,
        estimated_time_remaining: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update progress for an operation."""
        if operation_id not in self.operations:
            logger.warning(f"Attempted to update unknown operation {operation_id}")
            return False

        operation = self.operations[operation_id]

        # Update operation info
        operation.progress = max(0.0, min(100.0, progress))
        operation.message = message
        operation.updated_at = datetime.utcnow()

        if current_step is not None:
            operation.current_step = current_step

        if estimated_time_remaining is not None:
            operation.estimated_time_remaining = estimated_time_remaining

        if metadata:
            operation.metadata.update(metadata)

        # Create progress update
        update = ProgressUpdate(
            operation_id=operation_id,
            progress=operation.progress,
            status=operation.status.value,
            message=message,
            current_step=current_step,
            total_steps=operation.total_steps,
            estimated_time_remaining=estimated_time_remaining,
            metadata=metadata or {},
        )

        # Notify subscribers
        self._notify_subscribers(operation_id, update)

        # Call operation callbacks
        for callback in operation.callbacks:
            try:
                callback(update)
            except Exception as e:
                logger.error(f"Error in progress callback: {str(e)}")

        logger.debug(f"Updated operation {operation_id}: {progress:.1f}% - {message}")
        return True

    def complete_operation(
        self,
        operation_id: str,
        message: str = "Operation completed successfully",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Mark an operation as completed."""
        if operation_id not in self.operations:
            return False

        operation = self.operations[operation_id]
        operation.status = OperationStatus.COMPLETED
        operation.progress = 100.0
        operation.message = message
        operation.updated_at = datetime.utcnow()

        if metadata:
            operation.metadata.update(metadata)

        # Create final update
        update = ProgressUpdate(
            operation_id=operation_id,
            progress=100.0,
            status=OperationStatus.COMPLETED.value,
            message=message,
            metadata=metadata or {},
        )

        self._notify_subscribers(operation_id, update)

        logger.info(f"Completed operation {operation_id}: {message}")
        return True

    def fail_operation(
        self,
        operation_id: str,
        error_message: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Mark an operation as failed."""
        if operation_id not in self.operations:
            return False

        operation = self.operations[operation_id]
        operation.status = OperationStatus.FAILED
        operation.message = error_message
        operation.updated_at = datetime.utcnow()

        if metadata:
            operation.metadata.update(metadata)

        # Create failure update
        update = ProgressUpdate(
            operation_id=operation_id,
            progress=operation.progress,
            status=OperationStatus.FAILED.value,
            message=error_message,
            metadata=metadata or {},
        )

        self._notify_subscribers(operation_id, update)

        logger.error(f"Failed operation {operation_id}: {error_message}")
        return True

    def cancel_operation(
        self,
        operation_id: str,
        message: str = "Operation cancelled",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Mark an operation as cancelled."""
        if operation_id not in self.operations:
            return False

        operation = self.operations[operation_id]
        operation.status = OperationStatus.CANCELLED
        operation.message = message
        operation.updated_at = datetime.utcnow()

        if metadata:
            operation.metadata.update(metadata)

        # Create cancellation update
        update = ProgressUpdate(
            operation_id=operation_id,
            progress=operation.progress,
            status=OperationStatus.CANCELLED.value,
            message=message,
            metadata=metadata or {},
        )

        self._notify_subscribers(operation_id, update)

        logger.info(f"Cancelled operation {operation_id}: {message}")
        return True

    def get_operation_status(self, operation_id: str) -> dict[str, Any] | None:
        """Get the current status of an operation."""
        if operation_id not in self.operations:
            return None

        operation = self.operations[operation_id]
        return {
            "operation_id": operation.operation_id,
            "operation_type": operation.operation_type,
            "status": operation.status.value,
            "progress": operation.progress,
            "message": operation.message,
            "created_at": operation.created_at.isoformat(),
            "updated_at": operation.updated_at.isoformat(),
            "user_id": operation.user_id,
            "evidence_seeker_id": operation.evidence_seeker_id,
            "current_step": operation.current_step,
            "total_steps": operation.total_steps,
            "estimated_time_remaining": operation.estimated_time_remaining,
            "metadata": operation.metadata,
        }

    def get_user_operations(
        self,
        user_id: int,
        evidence_seeker_id: int | None = None,
        status_filter: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get all operations for a user, optionally filtered by evidence seeker and status."""
        operations = []

        for operation in self.operations.values():
            if operation.user_id != user_id:
                continue

            if (
                evidence_seeker_id is not None
                and operation.evidence_seeker_id != evidence_seeker_id
            ):
                continue

            if status_filter and operation.status.value not in status_filter:
                continue

            status = self.get_operation_status(operation.operation_id)
            if status is not None:
                operations.append(status)

        # Sort by creation time (most recent first)
        operations.sort(key=lambda x: x["created_at"], reverse=True)
        return operations

    def subscribe_to_operation(
        self, operation_id: str, callback: Callable[[ProgressUpdate], None]
    ) -> bool:
        """Subscribe to progress updates for an operation."""
        if operation_id not in self.operations:
            return False

        if operation_id not in self.subscribers:
            self.subscribers[operation_id] = []

        self.subscribers[operation_id].append(callback)
        return True

    def unsubscribe_from_operation(
        self, operation_id: str, callback: Callable[[ProgressUpdate], None]
    ) -> bool:
        """Unsubscribe from progress updates for an operation."""
        if operation_id not in self.subscribers:
            return False

        if callback in self.subscribers[operation_id]:
            self.subscribers[operation_id].remove(callback)
            return True

        return False

    def _notify_subscribers(self, operation_id: str, update: ProgressUpdate) -> None:
        """Notify all subscribers of an operation update."""
        if operation_id not in self.subscribers:
            return

        for callback in self.subscribers[operation_id]:
            try:
                callback(update)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {str(e)}")

    def cleanup_old_operations(self, max_age_hours: int = 24) -> None:
        """Clean up old completed/failed operations."""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        operations_to_remove = []

        for operation_id, operation in self.operations.items():
            if operation.updated_at.timestamp() < cutoff_time:
                if operation.status in [
                    OperationStatus.COMPLETED,
                    OperationStatus.FAILED,
                    OperationStatus.CANCELLED,
                ]:
                    operations_to_remove.append(operation_id)

        for operation_id in operations_to_remove:
            del self.operations[operation_id]
            if operation_id in self.subscribers:
                del self.subscribers[operation_id]

        if operations_to_remove:
            logger.info(f"Cleaned up {len(operations_to_remove)} old operations")

        # Limit stored events to a recent window for memory safety
        max_events = 500
        if len(self.events) > max_events:
            self.events = self.events[-max_events:]

    def record_event(
        self,
        name: str,
        user_id: int | None = None,
        evidence_seeker_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a lightweight analytics event for onboarding funnel metrics."""
        event = TrackerEvent(
            name=name,
            user_id=user_id,
            evidence_seeker_id=evidence_seeker_id,
            metadata=metadata or {},
        )
        self.events.append(event)
        if len(self.events) > 500:
            self.events = self.events[-500:]
        logger.info(
            "Recorded event %s (user_id=%s, seeker_id=%s)",
            name,
            user_id,
            evidence_seeker_id,
        )

    async def start_cleanup_task(self, interval_hours: int = 1) -> None:
        """Start the periodic cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            return

        async def cleanup_loop() -> None:
            while True:
                try:
                    self.cleanup_old_operations()
                    await asyncio.sleep(interval_hours * 3600)
                except Exception as e:
                    logger.error(f"Error in cleanup task: {str(e)}")
                    await asyncio.sleep(60)  # Wait a minute before retrying

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Started progress tracker cleanup task")


# Global instance
progress_tracker = ProgressTracker()
