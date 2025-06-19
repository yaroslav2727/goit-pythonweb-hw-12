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
from schemas import (
    UserCreate,
    Token,
    User,
    RequestEmail,
    RequestPasswordReset,
    ConfirmPasswordReset,
)
from src.services.auth import (
    create_access_token,
    Hash,
    get_email_from_token,
    get_email_from_password_reset_token,
    require_admin_role,
)
from src.services.users import UserService
from src.database.db import get_db
from src.database.models import UserRole
from src.services.email import send_email, send_password_reset_email
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
    """Register a new user account.

    Creates a new user account with the provided user data. Sends a verification
    email to the user's email address for account confirmation.

    Args:
        user_data (UserCreate): User registration data including username, email, and password.
        background_tasks (BackgroundTasks): FastAPI background tasks for sending emails.
        request (Request): The HTTP request object to get the base URL.
        db (AsyncSession): Database session dependency.

    Returns:
        User: The created user object.

    Raises:
        HTTPException: 409 Conflict if user with email or username already exists.
    """
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


@router.post(
    "/register-admin", response_model=User, status_code=status.HTTP_201_CREATED
)
async def register_admin_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only endpoint to create admin users.

    Creates a new admin user account. This endpoint requires admin privileges
    and sends a verification email to the new admin user.

    Args:
        user_data (UserCreate): Admin user data including username, email, and password.
        background_tasks (BackgroundTasks): FastAPI background tasks for sending emails.
        request (Request): The HTTP request object to get the base URL.
        current_user (User): Current authenticated admin user.
        db (AsyncSession): Database session dependency.

    Returns:
        User: The created admin user object.

    Raises:
        HTTPException: 409 Conflict if user with email or username already exists.
        HTTPException: 403 Forbidden if current user is not an admin.
    """
    user_service = UserService(db)

    email_user = await user_service.get_user_by_email(user_data.email)
    if email_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    username_user = await user_service.get_user_by_username(user_data.username)
    if username_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this username already exists",
        )

    user_data.password = Hash().get_password_hash(user_data.password)
    new_admin = await user_service.create_user(user_data, UserRole.ADMIN)

    try:
        background_tasks.add_task(
            send_email, new_admin.email, new_admin.username, str(request.base_url)
        )
        logger.info(f"Email confirmation queued for admin user {new_admin.email}")
    except Exception as e:
        logger.error(
            f"Failed to queue email confirmation for admin user {new_admin.email}: {e}"
        )

    return new_admin


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return access token.

    Validates user credentials and returns a JWT access token for authenticated requests.
    The user's email must be confirmed before login is allowed.

    Args:
        form_data (OAuth2PasswordRequestForm): User login credentials (username and password).
        db (AsyncSession): Database session dependency.

    Returns:
        Token: Access token and token type for authenticated API access.

    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid or email not confirmed.
    """
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
    """Confirm user's email address using verification token.

    Validates the email verification token and marks the user's email as confirmed.
    Users must confirm their email before they can log in.

    Args:
        token (str): Email verification token sent to user's email.
        db (AsyncSession): Database session dependency.

    Returns:
        dict: Success message confirming email verification.

    Raises:
        HTTPException: 400 Bad Request if token is invalid or user not found.
        HTTPException: 200 OK if email is already confirmed.
    """
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
    return {"message": "Електронну пошту підтверджено. Email confirmed successfully."}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Request email verification for user account.

    Sends a verification email to the user's email address. Returns a generic
    success message regardless of whether the email exists for security reasons.

    Args:
        body (RequestEmail): Request body containing the email address.
        background_tasks (BackgroundTasks): FastAPI background tasks for sending emails.
        request (Request): The HTTP request object to get the base URL.
        db (AsyncSession): Database session dependency.

    Returns:
        dict: Success message asking user to check their email.

    Raises:
        HTTPException: 500 Internal Server Error if email sending fails.
    """
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

    return {
        "message": "Перевірте свою електронну пошту для підтвердження. Check your email for confirmation instructions."
    }


@router.post("/request-password-reset")
async def request_password_reset(
    body: RequestPasswordReset,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Request password reset for user account.

    Sends a password reset email to the user's email address. Always returns
    a success message for security reasons, regardless of whether the email exists.

    Args:
        body (RequestPasswordReset): Request body containing the email address.
        background_tasks (BackgroundTasks): FastAPI background tasks for sending emails.
        request (Request): The HTTP request object to get the base URL.
        db (AsyncSession): Database session dependency.

    Returns:
        dict: Generic success message about password reset instructions.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)

    if user is not None:
        try:
            background_tasks.add_task(
                send_password_reset_email,
                user.email,
                user.username,
                str(request.base_url),
            )
            logger.info(f"Password reset email queued for {user.email}")
        except Exception as e:
            logger.error(f"Failed to queue password reset email for {user.email}: {e}")

    return {
        "message": "Якщо ваша електронна пошта зареєстрована, ви отримаєте інструкції для скидання пароля. If your email is registered, you will receive password reset instructions."
    }


@router.post("/confirm-password-reset")
async def confirm_password_reset(
    body: ConfirmPasswordReset,
    db: AsyncSession = Depends(get_db),
):
    """Confirm password reset using token and update user password.

    Validates the password reset token and updates the user's password
    with the new password provided in the request.

    Args:
        body (ConfirmPasswordReset): Request body containing email, new password, and reset token.
        db (AsyncSession): Database session dependency.

    Returns:
        dict: Success message confirming password reset.

    Raises:
        HTTPException: 400 Bad Request if token is invalid or expired.
        HTTPException: 404 Not Found if user doesn't exist.
    """
    try:
        token_email = await get_email_from_password_reset_token(body.token)

        if token_email != body.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token or email mismatch",
            )

        user_service = UserService(db)
        user = await user_service.get_user_by_email(body.email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        await user_service.update_password(body.email, body.new_password)

        logger.info(f"Password successfully reset for user {user.email}")

        return {
            "message": "Password has been successfully reset. Пароль успішно скинуто."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )
