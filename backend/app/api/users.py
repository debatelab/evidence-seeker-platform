from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users import FastAPIUsers
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import auth_backend, get_user_manager
from app.core.database import get_async_db
from app.core.permissions import require_platform_admin
from app.models.permission import UserRole
from app.models.user import User
from app.schemas.user import UserRead, UserSearchResult, UserUpdate

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


@router.get("/me", response_model=UserRead)
async def get_current_user(
    user: User = Depends(fastapi_users.current_user()),
) -> UserRead:
    """Get current authenticated user information"""
    return user


@router.put("/me", response_model=UserRead)
async def update_current_user(
    user_update: UserUpdate,
    user: User = Depends(fastapi_users.current_user()),
    session: AsyncSession = Depends(get_async_db),
) -> UserRead:
    """Update current user information"""
    # This would be handled by fastapi-users, but we can add custom logic here
    return user


@router.delete("/me")
async def delete_current_user(
    user: User = Depends(fastapi_users.current_user()),
) -> dict[str, str]:
    """Delete current user account"""
    # This would be handled by fastapi-users
    return {"message": "User account deleted successfully"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """
    Delete a user account. Only platform admins can delete users.
    """
    try:
        # Check if user exists
        from sqlalchemy import select

        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user_to_delete = result.scalar_one_or_none()
        if not user_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Prevent deleting the current user
        if user_to_delete.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account",
            )

        # Delete the user (this will cascade delete permissions due to foreign key constraints)
        await session.delete(user_to_delete)
        await session.commit()

        return {"message": "User deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}",
        ) from None


@router.get("/search-for-assignment", response_model=list[UserSearchResult])
async def search_users_for_assignment(
    q: str,
    current_user: User = Depends(fastapi_users.current_user()),
    session: AsyncSession = Depends(get_async_db),
) -> list[UserSearchResult]:
    """
    Search users by username/email for role assignment purposes.
    Returns username-only results (no emails) for GDPR compliance.
    Any authenticated user can search for role assignment.
    """
    try:
        # Log the incoming request for debugging
        logger.info(f"User search request: q='{q}', user_id={current_user.id}")
        if not q or len(q.strip()) < 2:
            logger.info("Search query too short, returning empty results")
            return []

        search_term = f"%{q.strip()}%"

        # Search by username only (GDPR compliance - no email exposure)
        from sqlalchemy import select

        logger.info(f"Executing search query with term: '{search_term}'")

        # Use ORM query instead of raw SQL for better async handling
        stmt = (
            select(User.id, User.username)
            .where(User.username.ilike(search_term), User.is_active)
            .order_by(User.username)
            .limit(20)
        )

        result = await session.execute(stmt)
        rows = result.all()
        logger.info(f"Found {len(rows)} users matching search")

        # Convert to proper UserSearchResult format
        user_results = [
            UserSearchResult(id=row.id, username=row.username) for row in rows
        ]

        logger.info(f"Returning {len(user_results)} user search results")
        return user_results

    except Exception as e:
        logger.error(f"Error in search_users_for_assignment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        ) from None


@router.get("/")
async def get_all_users(
    current_user: User = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_async_db),
) -> dict[str, list[dict[str, object]]]:
    """
    Get all users with role summaries. Only platform admins can view all users.
    Returns user info with simplified role display for platform admin interface.
    """
    try:
        # Get all users with full info for platform admins
        from sqlalchemy import func, select

        from app.models.permission import Permission

        # Get all users
        users_stmt = select(User).order_by(User.username)
        users_result = await session.execute(users_stmt)
        users = users_result.scalars().all()

        # Get permission summaries for each user
        user_summaries = []
        for user in users:
            # Check if user has PLATFORM_ADMIN role
            platform_admin_stmt = select(func.count(Permission.id)).where(
                Permission.user_id == user.id,
                Permission.role == UserRole.PLATFORM_ADMIN,
            )
            platform_admin_result = await session.execute(platform_admin_stmt)
            platform_admin_count = int(platform_admin_result.scalar_one())
            has_platform_admin = platform_admin_count > 0

            # Count total evidence seeker permissions (EVSE_ADMIN + EVSE_READER)
            evse_permissions_stmt = select(func.count(Permission.id)).where(
                Permission.user_id == user.id,
                Permission.role.in_([UserRole.EVSE_ADMIN, UserRole.EVSE_READER]),
            )
            evse_permissions_result = await session.execute(evse_permissions_stmt)
            evse_permissions_count: int = int(evse_permissions_result.scalar_one())

            # Determine display role and summary
            if has_platform_admin:
                display_role = "PLATFORM_ADMIN"
                role_summary = "Platform Admin"
                if evse_permissions_count > 0:
                    role_summary += f" + {evse_permissions_count} Evidence Seeker role{'s' if evse_permissions_count != 1 else ''}"
            elif evse_permissions_count > 0:
                display_role = "EVSE_ACCESS"
                role_summary = f"Evidence Seeker Access ({evse_permissions_count} role{'s' if evse_permissions_count != 1 else ''})"
            else:
                display_role = "NO_ACCESS"
                role_summary = "No roles assigned"

            user_summaries.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,  # Include email for platform admins
                    "isActive": user.is_active,
                    "displayRole": display_role,
                    "roleSummary": role_summary,
                    "hasPlatformAdmin": has_platform_admin,
                    "evidenceSeekerRolesCount": evse_permissions_count,
                }
            )

        return {"users": user_summaries}

    except Exception as e:
        logger.error(f"Error fetching all users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}",
        ) from None


@router.get("/test")
async def test_users_endpoint() -> dict[str, str]:
    """Test endpoint to verify user management endpoints are working"""
    return {"message": "User management endpoints are working!"}


# Error handlers for better error messages
