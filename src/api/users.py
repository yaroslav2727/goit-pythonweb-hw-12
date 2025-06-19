from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db import get_db
from src.database.redis_db import get_redis_cache, RedisCache

from schemas import User, UserRole
from src.database.models import UserRole as ModelUserRole
from src.conf.config import settings
from src.services.auth import get_current_user, require_admin_role
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel

from src.services.upload_file import UploadFileService
from src.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])

limiter = Limiter(key_func=get_remote_address)


class UserRoleUpdate(BaseModel):
    email: str
    role: UserRole


@router.get("/me", response_model=User)
@limiter.limit("3/minute")
async def me(request: Request, user: User = Depends(get_current_user)):
    """Get current user information.

    Returns the profile information of the currently authenticated user.
    Rate limited to 3 requests per minute.

    Args:
        request (Request): The HTTP request object.
        user (User): Currently authenticated user from JWT token.

    Returns:
        User: The current user's profile information.
    """
    return user


@router.patch("/avatar", response_model=User)
@limiter.limit("5/minute")
async def update_avatar_user(
    request: Request,
    file: UploadFile = File(..., description="Avatar image file (max 5MB)"),
    current_user: User = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_redis_cache),
):
    """Update user avatar image (Admin only).

    Uploads a new avatar image for the user to cloud storage and updates
    the user's profile. Requires admin privileges and confirmed email.
    Rate limited to 5 requests per minute.

    Args:
        request (Request): The HTTP request object.
        file (UploadFile): Avatar image file to upload (max 5MB).
        current_user (User): Currently authenticated admin user.
        db (AsyncSession): Database session dependency.
        cache (RedisCache): Redis cache dependency.

    Returns:
        User: Updated user object with new avatar URL.

    Raises:
        HTTPException: 403 Forbidden if email not confirmed or not admin.
        HTTPException: 404 Not Found if user doesn't exist.
        HTTPException: 500 Internal Server Error if upload fails.
    """
    try:
        if not current_user.confirmed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email must be confirmed before updating avatar",
            )

        upload_service = UploadFileService(
            settings.CLD_NAME, settings.CLD_API_KEY, settings.CLD_API_SECRET
        )
        avatar_url = upload_service.upload_file(file, current_user.username)

        user_service = UserService(db, cache)
        updated_user = await user_service.update_avatar_url(
            current_user.email, avatar_url
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return updated_user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не вдалося оновити аватар: {str(e)}",
        )


@router.delete("/avatar", response_model=User)
@limiter.limit("3/minute")
async def delete_avatar_user(
    request: Request,
    current_user: User = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_redis_cache),
):
    """Delete user avatar and reset to default Gravatar (Admin only).

    Removes the current avatar and resets it to the default Gravatar image
    based on the user's email. Requires admin privileges.
    Rate limited to 3 requests per minute.

    Args:
        request (Request): The HTTP request object.
        current_user (User): Currently authenticated admin user.
        db (AsyncSession): Database session dependency.
        cache (RedisCache): Redis cache dependency.

    Returns:
        User: Updated user object with default Gravatar avatar.

    Raises:
        HTTPException: 403 Forbidden if not admin.
        HTTPException: 404 Not Found if user doesn't exist.
        HTTPException: 500 Internal Server Error if operation fails.
    """
    try:
        from libgravatar import Gravatar

        g = Gravatar(current_user.email)
        default_avatar = g.get_image()

        user_service = UserService(db, cache)
        updated_user = await user_service.update_avatar_url(
            current_user.email, default_avatar
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return updated_user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не вдалося видалити аватар: {str(e)}",
        )


@router.patch("/role", response_model=User)
@limiter.limit("5/minute")
async def update_user_role(
    request: Request,
    role_update: UserRoleUpdate,
    current_user: User = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_redis_cache),
):
    """Update user role (Admin only).

    Updates a user's role in the system. This endpoint is restricted to admin users only.
    Rate limited to 5 requests per minute.

    Args:
        request (Request): The HTTP request object.
        role_update (UserRoleUpdate): Request body containing email and new role.
        current_user (User): Currently authenticated admin user.
        db (AsyncSession): Database session dependency.
        cache (RedisCache): Redis cache dependency.

    Returns:
        User: Updated user object with new role.

    Raises:
        HTTPException: 403 Forbidden if not admin.
        HTTPException: 404 Not Found if user doesn't exist.
        HTTPException: 500 Internal Server Error if operation fails.
    """
    try:
        user_service = UserService(db, cache)
        # Convert schema UserRole to model UserRole
        model_role = ModelUserRole(role_update.role.value)
        updated_user = await user_service.update_user_role(
            role_update.email, model_role
        )
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user role: {str(e)}",
        )
