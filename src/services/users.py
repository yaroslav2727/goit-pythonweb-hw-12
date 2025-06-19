from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from libgravatar import Gravatar
from fastapi import HTTPException, status
from passlib.context import CryptContext

from src.repository.users import UserRepository
from src.database.redis_db import RedisCache
from schemas import UserCreate
from src.database.models import UserRole


class UserService:
    """Service class for user-related operations.

    Provides high-level methods for user management including creation,
    retrieval, authentication, and profile updates. Acts as a layer
    between API endpoints and repository operations.

    Attributes:
        repository (UserRepository): The user repository for database operations.
        cache (Optional[RedisCache]): Redis cache for performance optimization.
    """

    def __init__(self, db: AsyncSession, cache: Optional[RedisCache] = None):
        """Initialize UserService with database session and optional cache.

        Args:
            db (AsyncSession): SQLAlchemy async database session.
            cache (Optional[RedisCache]): Redis cache instance for caching user data.
        """
        self.repository = UserRepository(db)
        self.cache = cache

    async def create_user(self, body: UserCreate, role: UserRole = UserRole.USER):
        """Create a new user account.

        Creates a new user with the provided data and generates a Gravatar
        avatar URL based on the user's email address.

        Args:
            body (UserCreate): User creation data including username, email, and password.
            role (UserRole): The role to assign to the user. Defaults to USER.

        Returns:
            User: The created user object.
        """
        avatar = None
        try:
            g = Gravatar(body.email)
            avatar = g.get_image()
        except Exception as e:
            print(f"Failed to get Gravatar: {e}")

        return await self.repository.create_user(body, avatar, role)

    async def get_user_by_id(self, user_id: int):
        """Retrieve a user by their ID.

        Args:
            user_id (int): The unique identifier of the user.

        Returns:
            User: The user object if found.

        Raises:
            HTTPException: 404 Not Found if user doesn't exist.
        """
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user

    async def get_user_by_username(self, username: str):
        """Retrieve a user by their username.

        Args:
            username (str): The username to search for.

        Returns:
            User | None: The user object if found, None otherwise.
        """
        return await self.repository.get_user_by_username(username)

    async def get_user_by_email(self, email: str):
        """Retrieve a user by their email address.

        Args:
            email (str): The email address to search for.

        Returns:
            User | None: The user object if found, None otherwise.
        """
        return await self.repository.get_user_by_email(email)

    async def confirmed_email(self, email: str):
        """Mark a user's email as confirmed.

        Updates the user's confirmed status to True, allowing them to log in.

        Args:
            email (str): The email address of the user to confirm.
        """
        return await self.repository.confirmed_email(email)

    async def update_avatar_url(self, email: str, url: str):
        """Update a user's avatar URL.

        Updates the user's avatar URL and invalidates their cache entry
        to ensure fresh data on subsequent requests.

        Args:
            email (str): The email address of the user.
            url (str): The new avatar URL.

        Returns:
            User: The updated user object.

        Raises:
            HTTPException: 404 Not Found if user doesn't exist.
        """
        try:
            user = await self.repository.update_avatar_url(email, url)
            if user and self.cache:
                await self.cache.delete_user(user.username)
            return user
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    async def update_password(self, email: str, new_password: str):
        """Update a user's password.

        Hashes the new password and updates it in the database.
        Invalidates the user's cache entry to ensure security.

        Args:
            email (str): The email address of the user.
            new_password (str): The new plain text password to set.

        Returns:
            User: The updated user object.

        Raises:
            HTTPException: 404 Not Found if user doesn't exist.
        """
        try:
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            hashed_password = pwd_context.hash(new_password)

            user = await self.repository.update_password(email, hashed_password)
            if user and self.cache:
                await self.cache.delete_user(user.username)
            return user
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    async def update_user_role(self, email: str, role: UserRole):
        """Update a user's role (admin operation).

        Updates the user's role in the system. This is typically restricted
        to admin users only. Invalidates the user's cache entry.

        Args:
            email (str): The email address of the user.
            role (UserRole): The new role to assign.

        Returns:
            User: The updated user object.

        Raises:
            HTTPException: 404 Not Found if user doesn't exist.
        """
        try:
            user = await self.repository.update_user_role(email, role)
            if user and self.cache:
                await self.cache.delete_user(user.username)
            return user
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
