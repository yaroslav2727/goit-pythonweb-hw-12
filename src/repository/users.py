from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, UserRole
from schemas import UserCreate


class UserRepository:
    """Repository class for user database operations.

    Provides low-level database operations for user entities including
    CRUD operations and user management functionality.

    Attributes:
        db (AsyncSession): SQLAlchemy async database session.
    """

    def __init__(self, session: AsyncSession):
        """Initialize UserRepository with database session.

        Args:
            session (AsyncSession): SQLAlchemy async database session.
        """
        self.db = session

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Retrieve a user by their unique ID.

        Args:
            user_id (int): The unique identifier of the user.

        Returns:
            User | None: The user object if found, None otherwise.
        """
        stmt = select(User).filter_by(id=user_id)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        """Retrieve a user by their username.

        Args:
            username (str): The username to search for.

        Returns:
            User | None: The user object if found, None otherwise.
        """
        stmt = select(User).filter_by(username=username)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Retrieve a user by their email address.

        Args:
            email (str): The email address to search for.

        Returns:
            User | None: The user object if found, None otherwise.
        """
        stmt = select(User).filter_by(email=email)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def create_user(
        self,
        body: UserCreate,
        avatar: str | None = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Create a new user in the database.

        Args:
            body (UserCreate): User creation data excluding password.
            avatar (str | None): URL of the user's avatar image.
            role (UserRole): The role to assign to the user.

        Returns:
            User: The created user object with assigned ID.
        """
        user = User(
            **body.model_dump(exclude_unset=True, exclude={"password"}),
            hashed_password=body.password,
            avatar=avatar,
            role=role
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def confirmed_email(self, email: str) -> None:
        """Mark a user's email as confirmed.

        Args:
            email (str): The email address of the user to confirm.
        """
        user = await self.get_user_by_email(email)
        if user:
            user.confirmed = True
            await self.db.commit()

    async def update_avatar_url(self, email: str, url: str) -> User:
        """Update a user's avatar URL.

        Args:
            email (str): The email address of the user.
            url (str): The new avatar URL.

        Returns:
            User: The updated user object.

        Raises:
            ValueError: If user with the email doesn't exist.
        """
        user = await self.get_user_by_email(email)
        if not user:
            raise ValueError("User not found")

        user.avatar = url
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_password(self, email: str, new_hashed_password: str) -> User:
        """Update a user's password hash.

        Args:
            email (str): The email address of the user.
            new_hashed_password (str): The new bcrypt hashed password.

        Returns:
            User: The updated user object.

        Raises:
            ValueError: If user with the email doesn't exist.
        """
        user = await self.get_user_by_email(email)
        if not user:
            raise ValueError("User not found")

        user.hashed_password = new_hashed_password
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_user_role(self, email: str, role: UserRole) -> User:
        """Update a user's role in the system.

        Updates the user's role, typically used for admin operations
        to promote/demote users.

        Args:
            email (str): The email address of the user.
            role (UserRole): The new role to assign.

        Returns:
            User: The updated user object.

        Raises:
            ValueError: If user with the email doesn't exist.
        """
        user = await self.get_user_by_email(email)
        if not user:
            raise ValueError("User not found")

        user.role = role
        await self.db.commit()
        await self.db.refresh(user)
        return user
