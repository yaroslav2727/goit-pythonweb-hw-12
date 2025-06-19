from datetime import datetime, timedelta, UTC
from typing import Optional

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from src.database.db import get_db
from src.database.redis_db import get_redis_cache, RedisCache
from src.services.users import UserService
from src.conf.config import settings
from src.database.models import UserRole


class Hash:
    """Password hashing utility class using bcrypt.

    Provides methods for hashing passwords and verifying password hashes
    using the bcrypt algorithm for secure password storage.
    """

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        """Verify a plain password against its hash.

        Args:
            plain_password (str): The plain text password to verify.
            hashed_password (str): The bcrypt hash to verify against.

        Returns:
            bool: True if password matches, False otherwise.
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        """Generate a bcrypt hash for a plain password.

        Args:
            password (str): The plain text password to hash.

        Returns:
            str: The bcrypt hash of the password.
        """
        return self.pwd_context.hash(password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_access_token(data: dict, expires_delta: Optional[int] = None):
    """Create a JWT access token.

    Generates a JWT token with the provided data and expiration time.
    Used for user authentication and authorization.

    Args:
        data (dict): The payload data to encode in the token.
        expires_delta (Optional[int]): Custom expiration time in seconds.
                                     If None, uses default from settings.

    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + timedelta(seconds=expires_delta)
    else:
        expire = datetime.now(UTC) + timedelta(seconds=settings.JWT_EXPIRATION_SECONDS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_redis_cache),
):
    """Get the current authenticated user from JWT token.

    Validates the JWT token, extracts the username, and retrieves the user
    from cache or database. Caches the user for subsequent requests.

    Args:
        token (str): JWT access token from Authorization header.
        db (AsyncSession): Database session dependency.
        cache (RedisCache): Redis cache dependency.

    Returns:
        User: The authenticated user object.

    Raises:
        HTTPException: 401 Unauthorized if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        username = payload["sub"]
        if username is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception  # Try to get user from cache first
    user = await cache.get_user(username)

    if user is None:
        # If not in cache, get from database and cache it
        user_service = UserService(db, cache)
        user = await user_service.get_user_by_username(username)
        if user is None:
            raise credentials_exception

        # Cache the user for future requests
        await cache.set_user(username, user, expire=settings.JWT_EXPIRATION_SECONDS)

    return user


def create_email_token(data: dict):
    """Create a JWT token for email verification.

    Generates a long-lived JWT token used for email verification.
    Token expires in 7 days.

    Args:
        data (dict): The payload data to encode in the token.

    Returns:
        str: The encoded JWT token for email verification.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=7)
    to_encode.update({"iat": datetime.now(UTC), "exp": expire})
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token


async def get_email_from_token(token: str):
    """Extract email from JWT verification token.

    Decodes and validates the JWT token to extract the email address.
    Used for email verification process.

    Args:
        token (str): JWT token containing email in the 'sub' claim.

    Returns:
        str: The email address from the token.

    Raises:
        HTTPException: 422 Unprocessable Entity if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        email = payload["sub"]
        return email
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email verification token",
        )


def create_password_reset_token(data: dict):
    """Create a JWT token for password reset.

    Generates a short-lived JWT token used for password reset verification.
    Token expires in 1 hour for security.

    Args:
        data (dict): The payload data to encode in the token.

    Returns:
        str: The encoded JWT token for password reset.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(
        hours=1
    )  # Short-lived token for password reset
    to_encode.update({"iat": datetime.now(UTC), "exp": expire})
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token


async def get_email_from_password_reset_token(token: str):
    """Extract email from password reset JWT token.

    Decodes and validates the password reset JWT token to extract the email address.
    Used for password reset confirmation process.

    Args:
        token (str): JWT password reset token containing email in the 'sub' claim.

    Returns:
        str: The email address from the token.

    Raises:
        HTTPException: 422 Unprocessable Entity if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        email = payload["sub"]
        return email
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid or expired password reset token",
        )


async def require_admin_role(current_user=Depends(get_current_user)):
    """Dependency to ensure current user has admin role.

    FastAPI dependency that checks if the current authenticated user
    has admin privileges. Used to protect admin-only endpoints.

    Args:
        current_user (User): The current authenticated user.

    Returns:
        User: The authenticated admin user.

    Raises:
        HTTPException: 403 Forbidden if user doesn't have admin role.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


def require_role(required_role: UserRole):
    """Factory function to create role-specific dependencies.

    Creates a FastAPI dependency function that checks if the current user
    has the specified role. Useful for creating role-based access control.

    Args:
        required_role (UserRole): The role required to access the endpoint.

    Returns:
        function: A dependency function that validates user role.
    """

    async def role_checker(current_user=Depends(get_current_user)):
        """Check if current user has the required role.

        Args:
            current_user (User): The current authenticated user.

        Returns:
            User: The authenticated user with required role.

        Raises:
            HTTPException: 403 Forbidden if user doesn't have required role.
        """
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. {required_role.value.title()} role required",
            )
        return current_user

    return role_checker
