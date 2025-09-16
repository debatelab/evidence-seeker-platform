"""
Pydantic schemas for API key management.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class APIKeyBase(BaseModel):
    """Base schema for API key data."""

    provider: str = Field(
        ..., description="API provider (e.g., 'huggingface', 'openai')"
    )
    name: str = Field(..., description="User-friendly name for the API key")
    description: Optional[str] = Field(None, description="Optional description")


class APIKeyCreate(APIKeyBase):
    """Schema for creating a new API key."""

    api_key: str = Field(..., description="The actual API key to encrypt and store")
    expires_in_days: Optional[int] = Field(
        None, description="Number of days until expiration"
    )


class APIKeyUpdate(BaseModel):
    """Schema for updating an API key."""

    name: Optional[str] = Field(None, description="Updated name")
    description: Optional[str] = Field(None, description="Updated description")
    is_active: Optional[bool] = Field(None, description="Whether the key is active")


class APIKeyRead(APIKeyBase):
    """Schema for reading API key data (without sensitive information)."""

    id: int
    user_id: int
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APIKeyReadWithHash(APIKeyRead):
    """Schema for reading API key data including hash (for validation)."""

    key_hash: str = Field(..., description="SHA-256 hash of the API key for validation")

    class Config:
        from_attributes = True


class APIKeyValidation(BaseModel):
    """Schema for API key validation requests."""

    provider: str = Field(..., description="API provider to validate against")
    api_key: str = Field(..., description="API key to validate")


class APIKeyValidationResponse(BaseModel):
    """Response schema for API key validation."""

    is_valid: bool = Field(..., description="Whether the API key format is valid")
    provider: str = Field(..., description="API provider that was validated")
    message: str = Field(..., description="Validation result message")
