"""
API endpoints for configuration management and API key operations.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.auth import get_current_user
from ..core.config_service import config_service
from ..core.database import get_db
from ..models.user import User
from ..schemas.api_key import (
    APIKeyCreate,
    APIKeyRead,
    APIKeyUpdate,
    APIKeyValidation,
    APIKeyValidationResponse,
)
from ..schemas.search import SearchStatistics

router = APIRouter()


@router.post("/{evidence_seeker_uuid}/api-keys", response_model=APIKeyRead)
def create_api_key(
    evidence_seeker_uuid: str,
    api_key_data: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIKeyRead:
    """Create and store an encrypted API key for an evidence seeker."""
    try:
        # Check if user has access to the evidence seeker
        from .evidence_seekers import get_evidence_seeker_by_identifier

        evidence_seeker = get_evidence_seeker_by_identifier(
            evidence_seeker_uuid, db, int(current_user.id)
        )
        # Extract scalar seeker_id value
        seeker_id: int = int(evidence_seeker.id)

        # Validate API key format
        if not config_service.validate_api_key_format(
            api_key_data.provider, api_key_data.api_key
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid API key format for provider {api_key_data.provider}",
            )

        # Create the API key
        api_key = config_service.create_api_key(
            evidence_seeker_id=seeker_id,
            provider=api_key_data.provider,
            name=api_key_data.name,
            api_key=api_key_data.api_key,
            description=api_key_data.description,
            expires_in_days=api_key_data.expires_in_days,
            db=db,
        )

        return APIKeyRead.from_orm(api_key)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create API key: {str(e)}"
        ) from e


@router.get("/{evidence_seeker_uuid}/api-keys", response_model=list[APIKeyRead])
def get_api_keys(
    evidence_seeker_uuid: str,
    provider: str | None = Query(None, description="Filter by provider"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[APIKeyRead]:
    """Get all API keys for an evidence seeker."""
    try:
        # Check if user has access to the evidence seeker
        from .evidence_seekers import get_evidence_seeker_by_identifier

        evidence_seeker = get_evidence_seeker_by_identifier(
            evidence_seeker_uuid, db, int(current_user.id)
        )
        # Extract scalar seeker_id value
        seeker_id: int = int(evidence_seeker.id)

        api_keys = config_service.get_api_keys_for_evidence_seeker(
            evidence_seeker_id=seeker_id, provider=provider, db=db
        )

        return [APIKeyRead.from_orm(key) for key in api_keys]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get API keys: {str(e)}"
        ) from e


@router.get("/{evidence_seeker_uuid}/api-keys/{api_key_id}", response_model=APIKeyRead)
def get_api_key(
    evidence_seeker_uuid: str,
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIKeyRead:
    """Get a specific API key for an evidence seeker."""
    try:
        # Check if user has access to the evidence seeker
        from .evidence_seekers import get_evidence_seeker_by_identifier

        evidence_seeker = get_evidence_seeker_by_identifier(
            evidence_seeker_uuid, db, int(current_user.id)
        )
        # Extract scalar seeker_id value
        seeker_id: int = int(evidence_seeker.id)

        api_key = config_service.get_api_key(
            api_key_id=api_key_id, evidence_seeker_id=seeker_id, db=db
        )

        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")

        return APIKeyRead.from_orm(api_key)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get API key: {str(e)}"
        ) from e


@router.put("/{evidence_seeker_uuid}/api-keys/{api_key_id}", response_model=APIKeyRead)
def update_api_key(
    evidence_seeker_uuid: str,
    api_key_id: int,
    api_key_data: APIKeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIKeyRead:
    """Update an API key for an evidence seeker."""
    try:
        # Check if user has access to the evidence seeker
        from .evidence_seekers import get_evidence_seeker_by_identifier

        evidence_seeker = get_evidence_seeker_by_identifier(
            evidence_seeker_uuid, db, int(current_user.id)
        )
        # Extract scalar seeker_id value
        seeker_id: int = int(evidence_seeker.id)

        success = config_service.update_api_key(
            api_key_id=api_key_id,
            evidence_seeker_id=seeker_id,
            name=api_key_data.name,
            description=api_key_data.description,
            is_active=api_key_data.is_active,
            db=db,
        )

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        # Get updated API key
        api_key = config_service.get_api_key(
            api_key_id=api_key_id, evidence_seeker_id=seeker_id, db=db
        )

        return APIKeyRead.from_orm(api_key)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update API key: {str(e)}"
        ) from e


@router.delete("/{evidence_seeker_uuid}/api-keys/{api_key_id}")
def delete_api_key(
    evidence_seeker_uuid: str,
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Delete (deactivate) an API key for an evidence seeker."""
    try:
        # Check if user has access to the evidence seeker
        from .evidence_seekers import get_evidence_seeker_by_identifier

        evidence_seeker = get_evidence_seeker_by_identifier(
            evidence_seeker_uuid, db, int(current_user.id)
        )

        success = config_service.delete_api_key(
            api_key_id=api_key_id, evidence_seeker_id=int(evidence_seeker.id), db=db
        )

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        return {"message": "API key deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete API key: {str(e)}"
        ) from e


@router.post("/api-keys/validate", response_model=APIKeyValidationResponse)
def validate_api_key_format(
    validation_data: APIKeyValidation,
    current_user: User = Depends(get_current_user),
) -> APIKeyValidationResponse:
    """Validate API key format for a provider."""
    try:
        is_valid = config_service.validate_api_key_format(
            validation_data.provider, validation_data.api_key
        )

        message = (
            f"Valid {validation_data.provider} API key format"
            if is_valid
            else f"Invalid {validation_data.provider} API key format"
        )

        return APIKeyValidationResponse(
            is_valid=is_valid, provider=validation_data.provider, message=message
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to validate API key: {str(e)}"
        ) from e


@router.get("/ai-config")
def get_ai_config() -> dict[str, Any]:
    """Get AI-related configuration settings."""
    try:
        return config_service.get_ai_config()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get AI config: {str(e)}"
        ) from e


@router.get("/system-stats", response_model=SearchStatistics)
def get_system_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchStatistics:
    """Get system statistics for AI components."""
    try:
        stats = config_service.get_system_stats(db=db)
        return SearchStatistics(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get system stats: {str(e)}"
        ) from e


@router.get("/providers")
def get_supported_providers() -> dict[str, Any]:
    """Get list of supported AI providers."""
    try:
        config = config_service.get_ai_config()
        return {
            "supported_providers": config["supported_providers"],
            "embedding_model": config["embedding_model"],
            "vector_dimensions": config["embedding_dimensions"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get providers: {str(e)}"
        ) from e


@router.post("/{evidence_seeker_uuid}/api-keys/{api_key_id}/decrypt")
def get_decrypted_api_key(
    evidence_seeker_uuid: str,
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str | int]:
    """Get a decrypted API key for use (use with caution)."""
    try:
        # Check if user has access to the evidence seeker
        from .evidence_seekers import get_evidence_seeker_by_identifier

        evidence_seeker = get_evidence_seeker_by_identifier(
            evidence_seeker_uuid, db, int(current_user.id)
        )

        decrypted_key = config_service.get_decrypted_api_key(
            api_key_id=api_key_id, evidence_seeker_id=int(evidence_seeker.id), db=db
        )

        if decrypted_key is None:
            raise HTTPException(
                status_code=404, detail="API key not found, expired, or inactive"
            )

        return {
            "api_key_id": api_key_id,
            "decrypted_key": decrypted_key,
            "warning": "This decrypted key should only be used immediately and not stored",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to decrypt API key: {str(e)}"
        ) from e
