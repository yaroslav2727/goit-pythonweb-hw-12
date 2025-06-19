import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, UTC
from fastapi import HTTPException
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import (
    Hash,
    create_access_token,
    get_current_user,
    create_email_token,
    get_email_from_token,
    create_password_reset_token,
    get_email_from_password_reset_token,
    require_admin_role,
    require_role,
)
from src.services.users import UserService
from src.database.models import User, UserRole
from src.database.redis_db import RedisCache
from src.conf.config import settings


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_cache():
    return AsyncMock(spec=RedisCache)


@pytest.fixture
def password_hash():
    hash_util = Hash()
    return hash_util.get_password_hash("12345678")


@pytest.fixture
def mock_user():
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        confirmed=True,
        role=UserRole.USER,
    )


@pytest.fixture
def mock_admin_user():
    return User(
        id=2,
        username="adminuser",
        email="admin@example.com",
        hashed_password="hashed_password",
        confirmed=True,
        role=UserRole.ADMIN,
    )


class TestHash:

    def test_get_password_hash(self):
        hash_util = Hash()
        password = "testpassword123"

        hashed_password = hash_util.get_password_hash(password)

        assert isinstance(hashed_password, str)
        assert len(hashed_password) > 0
        assert hashed_password != password

    def test_verify_password_correct(self, password_hash):
        hash_util = Hash()

        result = hash_util.verify_password("12345678", password_hash)

        assert result is True

    def test_verify_password_incorrect(self, password_hash):
        hash_util = Hash()

        result = hash_util.verify_password("wrongpassword", password_hash)

        assert result is False


class TestTokenOperations:

    def test_create_access_token(self):
        data = {"sub": "testuser"}

        token = create_access_token(data=data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiration(self):
        data = {"sub": "testuser"}
        expiration_time = 3600  # 1 hour

        token = create_access_token(data=data, expires_delta=expiration_time)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_email_token(self):
        email_data = {"sub": "test@example.com"}

        token = create_email_token(data=email_data)

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_get_email_from_token(self):
        email_data = {"sub": "test@example.com"}
        token = create_email_token(data=email_data)

        email = await get_email_from_token(token=token)

        assert email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_email_from_token_invalid(self):
        invalid_token = "invalid.token.string"

        with pytest.raises(HTTPException) as exc_info:
            await get_email_from_token(token=invalid_token)

        assert exc_info.value.status_code == 422

    def test_create_password_reset_token(self):
        email_data = {"sub": "test@example.com"}

        token = create_password_reset_token(data=email_data)

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_get_email_from_password_reset_token(self):
        email_data = {"sub": "test@example.com"}
        token = create_password_reset_token(data=email_data)

        email = await get_email_from_password_reset_token(token=token)

        assert email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_email_from_password_reset_token_invalid(self):
        invalid_token = "invalid.token.string"

        with pytest.raises(HTTPException) as exc_info:
            await get_email_from_password_reset_token(token=invalid_token)

        assert exc_info.value.status_code == 422


class TestGetCurrentUser:

    @pytest.mark.asyncio
    async def test_get_current_user_from_cache(self, mock_db, mock_cache, mock_user):
        token = create_access_token(data={"sub": "testuser"})
        mock_cache.get_user.return_value = mock_user

        result = await get_current_user(token=token, db=mock_db, cache=mock_cache)

        assert result == mock_user
        mock_cache.get_user.assert_called_once_with("testuser")

    @pytest.mark.asyncio
    async def test_get_current_user_from_database(self, mock_db, mock_cache, mock_user):
        token = create_access_token(data={"sub": "testuser"})
        mock_cache.get_user.return_value = None

        with patch.object(
            UserService, "get_user_by_username", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.return_value = mock_user

            result = await get_current_user(token=token, db=mock_db, cache=mock_cache)

            assert result == mock_user
            mock_cache.get_user.assert_called_once_with("testuser")
            mock_cache.set_user.assert_called_once_with(
                "testuser", mock_user, expire=settings.JWT_EXPIRATION_SECONDS
            )

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, mock_db, mock_cache):
        invalid_token = "invalid.token.string"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=invalid_token, db=mock_db, cache=mock_cache)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self, mock_db, mock_cache):
        token = create_access_token(data={"sub": "nonexistentuser"})
        mock_cache.get_user.return_value = None

        with patch.object(
            UserService, "get_user_by_username", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token=token, db=mock_db, cache=mock_cache)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_token_without_sub(self, mock_db, mock_cache):
        data = {"user_id": 1}
        token = create_access_token(data=data)

        with pytest.raises(KeyError):
            await get_current_user(token=token, db=mock_db, cache=mock_cache)


class TestRoleBasedAccess:

    @pytest.mark.asyncio
    async def test_require_admin_role_success(self, mock_admin_user):
        result = await require_admin_role(current_user=mock_admin_user)

        assert result == mock_admin_user

    @pytest.mark.asyncio
    async def test_require_admin_role_failure(self, mock_user):
        with pytest.raises(HTTPException) as exc_info:
            await require_admin_role(current_user=mock_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_role_success(self, mock_user):
        role_checker = require_role(UserRole.USER)

        result = await role_checker(current_user=mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_role_failure(self, mock_user):
        role_checker = require_role(UserRole.ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            await role_checker(current_user=mock_user)

        assert exc_info.value.status_code == 403
