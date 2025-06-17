from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Security,
    BackgroundTasks,
    Request,
)
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from schemas import UserCreate, Token, User, RequestEmail
from src.services.auth import create_access_token, Hash, get_email_from_token
from src.services.users import UserService
from src.database.db import get_db
from src.services.email import send_email
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_service = UserService(db)

    email_user = await user_service.get_user_by_email(user_data.email)
    if email_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з таким email вже існує",
        )

    username_user = await user_service.get_user_by_username(user_data.username)
    if username_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з таким іменем вже існує",
        )
    user_data.password = Hash().get_password_hash(user_data.password)
    new_user = await user_service.create_user(user_data)

    try:
        background_tasks.add_task(
            send_email, new_user.email, new_user.username, str(request.base_url)
        )
        logger.info(f"Email для підтвердження для {new_user.email} в черзі")
    except Exception as e:
        logger.error(
            f"Не вдалося поставити в чергу email для підтвердження для {new_user.email}: {e}"
        )

    return new_user


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    user = await user_service.get_user_by_username(form_data.username)
    if not user or not Hash().verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильний логін або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Електронна адреса не підтверджена",
        )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    email = await get_email_from_token(token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ваша електронна пошта вже підтверджена",
        )

    await user_service.confirmed_email(email)
    return {"message": "Електронну пошту підтверджено"}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)

    if user is None:
        return {"message": "Перевірте свою електронну пошту для підтвердження"}

    if user.confirmed:
        return {"message": "Ваша електронна пошта вже підтверджена"}

    try:
        background_tasks.add_task(
            send_email, user.email, user.username, str(request.base_url)
        )
        logger.info(f"Email для підтвердження для {user.email} в черзі")
    except Exception as e:
        logger.error(
            f"Не вдалося поставити в чергу email для підтвердження для {user.email}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не вдалося надіслати email. Перевірте налаштування пошти.",
        )

    return {"message": "Перевірте свою електронну пошту для підтвердження"}
