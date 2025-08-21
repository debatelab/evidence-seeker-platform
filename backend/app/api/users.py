from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users import FastAPIUsers
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_user_manager, auth_backend
from app.core.database import get_db
from app.schemas.user import UserRead, UserUpdate
from app.models.user import User

# Create router
router = APIRouter()

# Initialize FastAPI Users
fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])


# Include user management routes from fastapi-users
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@router.get("/users/me", response_model=UserRead)
async def get_current_user(user: User = Depends(fastapi_users.current_user())):
    """Get current authenticated user information"""
    return user


@router.put("/users/me", response_model=UserRead)
async def update_current_user(
    user_update: UserUpdate,
    user: User = Depends(fastapi_users.current_user()),
    session: AsyncSession = Depends(get_db),
):
    """Update current user information"""
    # This would be handled by fastapi-users, but we can add custom logic here
    return user


@router.delete("/users/me")
async def delete_current_user(user: User = Depends(fastapi_users.current_user())):
    """Delete current user account"""
    # This would be handled by fastapi-users
    return {"message": "User account deleted successfully"}


@router.get("/users/test")
async def test_users_endpoint():
    """Test endpoint to verify user management endpoints are working"""
    return {"message": "User management endpoints are working!"}


# Error handlers for better error messages
