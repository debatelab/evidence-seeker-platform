from datetime import datetime

from fastapi_users import schemas
from pydantic import BaseModel, EmailStr, Field

try:
    # Pydantic v2
    from pydantic import ConfigDict  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback for older versions
    ConfigDict = dict  # type: ignore[misc,assignment]


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase for JSON aliases."""
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class UserRead(schemas.BaseUser[int]):
    """User schema for reading user data"""

    id: int
    email: EmailStr
    username: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Pydantic v2 style config to allow ORM objects and camelCase JSON
    model_config = ConfigDict(  # type: ignore[call-arg]
        populate_by_name=True,
        from_attributes=True,
        alias_generator=to_camel,
    )


class UserCreate(schemas.BaseUserCreate):
    """User schema for user creation"""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str
    is_active: bool | None = True
    is_superuser: bool | None = False
    is_verified: bool | None = False


class UserUpdate(schemas.BaseUserUpdate):
    """User schema for user updates"""

    email: EmailStr | None = None
    username: str | None = Field(
        None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"
    )
    password: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_verified: bool | None = None


class UserInDB(UserRead):
    """User schema for database representation"""

    hashed_password: str


class Token(BaseModel):
    """JWT token schema"""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT token data schema"""

    email: str | None = None
    user_id: int | None = None


class LoginRequest(BaseModel):
    """Login request schema"""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Registration request schema"""

    email: EmailStr
    username: str | None = Field(
        default=None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"
    )
    password: str


class UserResponse(BaseModel):
    """Generic user response schema"""

    user: UserRead
    message: str = "Operation successful"


class AuthResponse(BaseModel):
    """Authentication response schema"""

    user: UserRead
    access_token: str
    token_type: str = "bearer"
    message: str = "Authentication successful"


class UserSearchResult(BaseModel):
    """User search result schema for role assignment"""

    id: int
    username: str

    # Allow ORM conversion and camelCase JSON
    model_config = ConfigDict(  # type: ignore[call-arg]
        from_attributes=True,
        alias_generator=to_camel,
    )
