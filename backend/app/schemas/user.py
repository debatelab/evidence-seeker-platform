from fastapi_users import schemas
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserRead(schemas.BaseUser[int]):
    """User schema for reading user data"""

    id: int
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserCreate(schemas.BaseUserCreate):
    """User schema for user creation"""

    email: EmailStr
    password: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False


class UserUpdate(schemas.BaseUserUpdate):
    """User schema for user updates"""

    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserInDB(UserRead):
    """User schema for database representation"""

    hashed_password: str


class Token(BaseModel):
    """JWT token schema"""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT token data schema"""

    email: Optional[str] = None
    user_id: Optional[int] = None


class LoginRequest(BaseModel):
    """Login request schema"""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Registration request schema"""

    email: EmailStr
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
