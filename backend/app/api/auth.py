from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import auth_backend, get_user_manager, UserManager
from app.core.database import get_db
from app.schemas.user import UserRead, UserCreate
from app.models.user import User

# Create router
router = APIRouter()

# Initialize FastAPI Users
fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])

# Security scheme for documentation
security = HTTPBearer()

# Include auth routes from fastapi-users
router.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)

router.include_router(
    fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"]
)


@router.post("/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout endpoint - in JWT, logout is handled client-side by removing token"""
    return {"message": "Successfully logged out"}


@router.get("/auth/me", response_model=UserRead)
async def get_current_user(user: User = Depends(fastapi_users.current_user())):
    """Get current authenticated user"""
    return user


@router.get("/auth/test")
async def test_auth_endpoint():
    """Test endpoint to verify authentication is working"""
    return {"message": "Authentication endpoints are working!"}


# Error handlers for better error messages
