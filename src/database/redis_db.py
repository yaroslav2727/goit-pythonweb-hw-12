import json
import pickle
from typing import Optional, Any
import redis.asyncio as redis
from src.conf.config import settings
from src.database.models import User


class RedisCache:
    """Redis cache manager for user data and session management.

    This class provides methods to cache, retrieve, and manage user data
    in Redis for improved application performance and session handling.
    """

    def __init__(self):
        """Initialize Redis connection based on configuration settings.

        Creates a Redis client instance using either REDIS_URL or individual
        connection parameters from the application settings.
        """
        if settings.REDIS_URL:
            self.redis = redis.from_url(settings.REDIS_URL)
        else:
            self.redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=False,
            )

    async def get_user(self, username: str) -> Optional[User]:
        """Get user from cache.

        Retrieves a cached user object from Redis using the username as key.

        Args:
            username (str): The username to look up in cache.

        Returns:
            Optional[User]: The cached User object if found, None otherwise.
        """
        try:
            cached_user = await self.redis.get(f"user:{username}")
            if cached_user:
                user_data = pickle.loads(cached_user)
                return user_data
            return None
        except Exception as e:
            print(f"Redis get error: {e}")
            return None

    async def set_user(self, username: str, user: User, expire: int = 3600) -> bool:
        """Cache user data.

        Stores a user object in Redis cache with an optional expiration time.

        Args:
            username (str): The username to use as cache key.
            user (User): The User object to cache.
            expire (int, optional): Cache expiration time in seconds. Defaults to 3600.

        Returns:
            bool: True if caching was successful, False otherwise.
        """
        try:
            user_data = pickle.dumps(user)
            await self.redis.setex(f"user:{username}", expire, user_data)
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    async def delete_user(self, username: str) -> bool:
        """Remove user from cache.

        Deletes a user's cached data from Redis.

        Args:
            username (str): The username whose cache entry should be deleted.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        try:
            await self.redis.delete(f"user:{username}")
            return True
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False

    async def clear_all_users(self) -> bool:
        """Clear all cached users (useful for testing or cleanup).

        Removes all user cache entries from Redis by deleting all keys
        that match the "user:*" pattern.

        Returns:
            bool: True if clearing was successful, False otherwise.
        """
        try:
            keys = await self.redis.keys("user:*")
            if keys:
                await self.redis.delete(*keys)
            return True
        except Exception as e:
            print(f"Redis clear error: {e}")
            return False

    async def ping(self) -> bool:
        """Check if Redis is accessible.

        Tests the Redis connection by sending a ping command.

        Returns:
            bool: True if Redis is accessible and responding, False otherwise.
        """
        try:
            return await self.redis.ping()
        except Exception as e:
            print(f"Redis ping error: {e}")
            return False

    async def close(self):
        """Close Redis connection.

        Properly closes the Redis connection to free up resources.
        Should be called when the cache instance is no longer needed.
        """
        try:
            await self.redis.close()
        except Exception as e:
            print(f"Redis close error: {e}")


redis_cache = RedisCache()


async def get_redis_cache() -> RedisCache:
    """Dependency to get Redis cache instance.

    This function serves as a FastAPI dependency to inject the Redis cache
    instance into route handlers and other components that need caching functionality.

    Returns:
        RedisCache: The global Redis cache instance.
    """
    return redis_cache
