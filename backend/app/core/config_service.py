"""
Configuration Service for managing encrypted API keys and AI settings.
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.models import APIKey, User
from app.core.config import settings

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for managing encrypted configuration and API keys."""

    def __init__(self):
        # Generate or load encryption key
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for API key storage."""
        key_file = os.path.join(os.path.dirname(__file__), "..", "..", "encryption_key")

        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            # Ensure directory exists
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, "wb") as f:
                f.write(key)
            logger.info("Generated new encryption key for API key storage")
            return key

    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt an API key for storage."""
        try:
            encrypted = self.fernet.encrypt(api_key.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Failed to encrypt API key: {str(e)}")
            raise

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt an API key for use."""
        try:
            decrypted = self.fernet.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {str(e)}")
            raise

    def create_api_key(
        self,
        evidence_seeker_id: int,
        provider: str,
        name: str,
        api_key: str,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        db: Session = None,
    ) -> APIKey:
        """Create and store an encrypted API key."""
        if db is None:
            # Create a new session if not provided
            from app.core.database import SessionLocal

            db = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            # Check if evidence seeker exists
            from app.models import EvidenceSeeker

            evidence_seeker = (
                db.query(EvidenceSeeker)
                .filter(EvidenceSeeker.id == evidence_seeker_id)
                .first()
            )
            if not evidence_seeker:
                raise ValueError(f"Evidence Seeker {evidence_seeker_id} not found")

            # Encrypt the API key
            encrypted_key = self.encrypt_api_key(api_key)

            # Create hash for validation
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()

            # Calculate expiration date
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

            # Create API key record
            api_key_record = APIKey(
                evidence_seeker_id=evidence_seeker_id,
                evidence_seeker_uuid=evidence_seeker.uuid,
                encrypted_key=encrypted_key,
                key_hash=key_hash,
                provider=provider,
                name=name,
                description=description,
                expires_at=expires_at,
            )

            db.add(api_key_record)
            db.commit()
            db.refresh(api_key_record)

            logger.info(
                f"Created API key '{name}' for evidence seeker {evidence_seeker_id} with provider {provider}"
            )
            return api_key_record

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create API key: {str(e)}")
            raise
        finally:
            if should_close:
                db.close()

    def get_api_key(
        self, api_key_id: int, evidence_seeker_id: int, db: Session = None
    ) -> Optional[APIKey]:
        """Get an API key record for an evidence seeker."""
        if db is None:
            from app.core.database import SessionLocal

            db = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            api_key = (
                db.query(APIKey)
                .filter(
                    APIKey.id == api_key_id,
                    APIKey.evidence_seeker_id == evidence_seeker_id,
                    APIKey.is_active == True,
                )
                .first()
            )

            return api_key
        finally:
            if should_close:
                db.close()

    def get_api_keys_for_evidence_seeker(
        self,
        evidence_seeker_id: int,
        provider: Optional[str] = None,
        db: Session = None,
    ) -> List[APIKey]:
        """Get all API keys for an evidence seeker, optionally filtered by provider."""
        if db is None:
            from app.core.database import SessionLocal

            db = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            query = db.query(APIKey).filter(
                APIKey.evidence_seeker_id == evidence_seeker_id,
                APIKey.is_active == True,
            )

            if provider:
                query = query.filter(APIKey.provider == provider)

            return query.all()
        finally:
            if should_close:
                db.close()

    def get_decrypted_api_key(
        self, api_key_id: int, evidence_seeker_id: int, db: Session = None
    ) -> Optional[str]:
        """Get a decrypted API key for use."""
        api_key_record = self.get_api_key(api_key_id, evidence_seeker_id, db)
        if not api_key_record:
            return None

        if not api_key_record.is_valid:
            logger.warning(f"API key {api_key_id} is not valid (expired or inactive)")
            return None

        try:
            decrypted_key = self.decrypt_api_key(api_key_record.encrypted_key)
            # Update last used timestamp
            if db is None:
                from app.core.database import SessionLocal

                db = SessionLocal()
                should_close = True
            else:
                should_close = False

            try:
                api_key_record.last_used_at = datetime.utcnow()
                db.commit()
            finally:
                if should_close:
                    db.close()

            return decrypted_key
        except Exception as e:
            logger.error(f"Failed to decrypt API key {api_key_id}: {str(e)}")
            return None

    def update_api_key(
        self,
        api_key_id: int,
        evidence_seeker_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        db: Session = None,
    ) -> bool:
        """Update an API key record."""
        if db is None:
            from app.core.database import SessionLocal

            db = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            api_key = (
                db.query(APIKey)
                .filter(
                    APIKey.id == api_key_id,
                    APIKey.evidence_seeker_id == evidence_seeker_id,
                )
                .first()
            )

            if not api_key:
                return False

            if name is not None:
                api_key.name = name
            if description is not None:
                api_key.description = description
            if is_active is not None:
                api_key.is_active = is_active

            api_key.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"Updated API key {api_key_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update API key {api_key_id}: {str(e)}")
            return False
        finally:
            if should_close:
                db.close()

    def delete_api_key(
        self, api_key_id: int, evidence_seeker_id: int, db: Session = None
    ) -> bool:
        """Soft delete an API key (mark as inactive)."""
        return self.update_api_key(
            api_key_id=api_key_id,
            evidence_seeker_id=evidence_seeker_id,
            is_active=False,
            db=db,
        )

    def validate_api_key_format(self, provider: str, api_key: str) -> bool:
        """Validate API key format for a specific provider."""
        if not api_key or not api_key.strip():
            return False

        # Provider-specific validation rules
        if provider.lower() == "huggingface":
            # HuggingFace API keys start with "hf_"
            return api_key.startswith("hf_") and len(api_key) > 10
        elif provider.lower() == "openai":
            # OpenAI API keys start with "sk-"
            return api_key.startswith("sk-") and len(api_key) > 20
        else:
            # Generic validation - just check it's not empty and reasonable length
            return len(api_key) > 10

    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI-related configuration settings."""
        return {
            "embedding_model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            "embedding_dimensions": 768,
            "chunk_size": 512,
            "chunk_overlap": 50,
            "max_concurrent_embeddings": 3,
            "supported_providers": ["huggingface", "openai"],
            "default_similarity_threshold": 0.1,
            "max_search_results": 50,
        }

    def get_system_stats(self, db: Session = None) -> Dict[str, Any]:
        """Get system statistics for AI components."""
        if db is None:
            from app.core.database import SessionLocal

            db = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            from app.models import Document, Embedding

            total_documents = db.query(Document).count()
            documents_with_embeddings = (
                db.query(Document)
                .filter(Document.embedding_status == "COMPLETED")
                .count()
            )
            total_embeddings = db.query(Embedding).count()
            total_api_keys = db.query(APIKey).filter(APIKey.is_active == True).count()

            return {
                "total_documents": total_documents,
                "documents_with_embeddings": documents_with_embeddings,
                "total_embeddings": total_embeddings,
                "total_api_keys": total_api_keys,
                "embedding_coverage": (
                    documents_with_embeddings / total_documents
                    if total_documents > 0
                    else 0
                ),
            }
        finally:
            if should_close:
                db.close()


# Global instance
config_service = ConfigService()
