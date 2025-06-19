from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.database.db import get_db
from src.database.redis_db import get_redis_cache, RedisCache

router = APIRouter(tags=["utils"])


@router.get("/healthchecker")
async def healthchecker(
    db: AsyncSession = Depends(get_db), cache: RedisCache = Depends(get_redis_cache)
):
    """Check the health status of the application and its dependencies.

    Verifies connectivity to the database and Redis cache to ensure
    the application is functioning properly.

    Args:
        db (AsyncSession): Database session dependency.
        cache (RedisCache): Redis cache dependency.

    Returns:
        dict: Health status including database and Redis connectivity.

    Raises:
        HTTPException: 500 Internal Server Error if connections fail.
    """
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        result = result.scalar_one_or_none()

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database is not configured correctly",
            )

        # Test Redis connection
        redis_status = await cache.ping()

        return {
            "message": "Welcome to FastAPI!",
            "database": "connected",
            "redis": "connected" if redis_status else "disconnected",
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error connecting to the database or Redis",
        )
