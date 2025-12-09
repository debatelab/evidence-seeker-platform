from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi_users import FastAPIUsers

from app.core.config import settings
from app.core.auth import UserManager, auth_backend, get_user_manager
from app.models.user import FastAPIUser
from app.schemas.user import UserCreate, UserRead

# Create router
router = APIRouter()

# Initialize FastAPI Users
fastapi_users = FastAPIUsers[FastAPIUser, int](get_user_manager, [auth_backend])

# Security scheme for documentation
security = HTTPBearer()

# Include auth routes from fastapi-users
router.include_router(
    fastapi_users.get_auth_router(
        auth_backend, requires_verification=settings.is_email_verification_required
    ),
    prefix="/auth/jwt",
    tags=["auth"],
)

# Default register route from fastapi-users
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
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, str]:
    """Logout endpoint - in JWT, logout is handled client-side by removing token"""
    return {"message": "Successfully logged out"}


@router.get("/auth/me", response_model=UserRead)
async def get_current_user(
    user: FastAPIUser = Depends(fastapi_users.current_user()),
) -> UserRead:
    """Get current authenticated user"""
    return UserRead.model_validate(user)


@router.post("/auth/resend-verification")
async def resend_verification(
    request: Request,
    user_manager: UserManager = Depends(get_user_manager),
    current_user: FastAPIUser = Depends(fastapi_users.current_user()),
) -> dict[str, str]:
    """Resend verification email to current user"""
    try:
        await user_manager.request_verify(current_user, request)
        return {"message": "Verification email sent successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification email: {str(e)}",
        ) from e


@router.get("/auth/test")
async def test_auth_endpoint() -> dict[str, str]:
    """Test endpoint to verify authentication is working"""
    return {"message": "Authentication endpoints are working!"}


# Error handlers for better error messages
