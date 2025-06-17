from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db import get_db

from schemas import User
from src.conf.config import settings
from src.services.auth import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.services.upload_file import UploadFileService
from src.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])

limiter = Limiter(key_func=get_remote_address)


@router.get("/me", response_model=User)
@limiter.limit("3/minute")
async def me(request: Request, user: User = Depends(get_current_user)):
    return user


@router.patch("/avatar", response_model=User)
@limiter.limit("5/minute")
async def update_avatar_user(
    request: Request,
    file: UploadFile = File(..., description="Avatar image file (max 5MB)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

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

        user_service = UserService(db)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    try:
        from libgravatar import Gravatar

        g = Gravatar(current_user.email)
        default_avatar = g.get_image()

        user_service = UserService(db)
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
