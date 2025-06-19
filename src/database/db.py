import contextlib

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from src.conf.config import settings


class DatabaseSessionManager:
    """Manages database sessions and connection lifecycle.

    This class provides a centralized way to manage database connections
    and sessions using SQLAlchemy's async engine and session maker.
    """

    def __init__(self, url: str):
        """Initialize the database session manager.

        Args:
            url (str): Database connection URL.
        """
        self._engine: AsyncEngine | None = create_async_engine(url)
        self._session_maker: async_sessionmaker = async_sessionmaker(
            autoflush=False, autocommit=False, bind=self._engine
        )

    @contextlib.asynccontextmanager
    async def session(self):
        """Create and manage a database session context.

        This async context manager ensures proper session lifecycle management,
        including automatic rollback on errors and session cleanup.

        Yields:
            AsyncSession: An async database session.

        Raises:
            Exception: If the database session is not initialized.
            SQLAlchemyError: If a database error occurs during the session.
        """
        if self._session_maker is None:
            raise Exception("Database session is not initialized")
        session = self._session_maker()
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(settings.DB_URL)


async def get_db():
    """Dependency function to get a database session.

    This function is typically used as a FastAPI dependency to inject
    database sessions into route handlers.

    Yields:
        AsyncSession: An async database session for use in API endpoints.
    """
    async with sessionmanager.session() as session:
        yield session
