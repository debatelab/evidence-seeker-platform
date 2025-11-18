"""Utility helpers for issuing and validating short-lived onboarding tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.evidence_seeker import EvidenceSeeker
from app.models.evidence_seeker_settings import EvidenceSeekerSettings


class OnboardingTokenService:
    """Issue, validate, and revoke onboarding tokens used during the wizard."""

    def __init__(self) -> None:
        self._secret = settings.jwt_secret_key
        self._algorithm = settings.jwt_algorithm
        self._lifetime = timedelta(hours=24)

    def issue_token(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        owner_user_id: int,
    ) -> str:
        """Generate a signed token and persist its metadata on the settings row."""
        settings_row = seeker.settings or EvidenceSeekerSettings(
            evidence_seeker_id=seeker.id,
        )
        if seeker.settings is None:
            db.add(settings_row)
            db.commit()
            db.refresh(settings_row)

        jti = uuid4().hex
        expires_at = datetime.now(timezone.utc) + self._lifetime
        payload = {
            "sub": str(owner_user_id),
            "seeker_uuid": str(seeker.uuid),
            "jti": jti,
            "exp": expires_at,
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)

        settings_row.onboarding_token_jti = jti
        settings_row.onboarding_token_owner_id = owner_user_id
        settings_row.onboarding_token_expires_at = expires_at.replace(tzinfo=None)
        db.commit()
        db.refresh(settings_row)
        return token

    def revoke_token(self, db: Session, settings_row: EvidenceSeekerSettings) -> None:
        """Clear stored onboarding token metadata."""
        settings_row.onboarding_token_jti = None
        settings_row.onboarding_token_owner_id = None
        settings_row.onboarding_token_expires_at = None
        db.commit()
        db.refresh(settings_row)

    def verify_token(
        self,
        token: str,
        seeker: EvidenceSeeker,
        current_user_id: int,
    ) -> bool:
        """Validate token signature and metadata against the stored values."""
        settings_row = seeker.settings
        if settings_row is None:
            return False
        if not settings_row.onboarding_token_jti:
            return False

        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )
        except JWTError:
            return False

        if payload.get("sub") != str(current_user_id):
            return False

        if payload.get("seeker_uuid") != str(seeker.uuid):
            return False

        if payload.get("jti") != settings_row.onboarding_token_jti:
            return False

        expires_at = settings_row.onboarding_token_expires_at
        if expires_at and expires_at < datetime.utcnow():
            return False

        if (
            settings_row.onboarding_token_owner_id is not None
            and settings_row.onboarding_token_owner_id != current_user_id
        ):
            return False

        return True


onboarding_token_service = OnboardingTokenService()
