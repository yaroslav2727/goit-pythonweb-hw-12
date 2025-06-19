import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from src.services.users import UserService
from src.repository.users import UserRepository
from src.database.redis_db import RedisCache
from src.database.models import User, UserRole
from schemas import UserCreate


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_cache():
    return AsyncMock(spec=RedisCache)


@pytest.fixture
def user_service(mock_db, mock_cache):
    return UserService(mock_db, mock_cache)


@pytest.fixture
def user_service_no_cache(mock_db):
    return UserService(mock_db)


@pytest.fixture
def sample_user():
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        confirmed=False,
        role=UserRole.USER,
        avatar="http://example.com/avatar.png",
    )


@pytest.fixture
def admin_user():
    return User(
        id=2,
        username="adminuser",
        email="admin@example.com",
        hashed_password="hashed_admin_password",
        confirmed=True,
        role=UserRole.ADMIN,
        avatar="http://example.com/admin_avatar.png",
    )


class TestUserService:

    def test_user_service_initialization_with_cache(self, user_service):
        assert user_service.repository is not None
        assert isinstance(user_service.repository, UserRepository)
        assert user_service.cache is not None

    def test_user_service_initialization_without_cache(self, user_service_no_cache):
        assert user_service_no_cache.repository is not None
        assert isinstance(user_service_no_cache.repository, UserRepository)
        assert user_service_no_cache.cache is None

    @pytest.mark.asyncio
    async def test_create_user_default_role(self, user_service):
        user_data = UserCreate(
            username="newuser", email="new@example.com", password="securepassword"
        )

        with patch("src.services.users.Gravatar") as mock_gravatar_class:
            mock_gravatar = MagicMock()
            mock_gravatar.get_image.return_value = "http://gravatar.com/avatar/hash"
            mock_gravatar_class.return_value = mock_gravatar

            with patch("src.services.users.CryptContext") as mock_crypt:
                mock_crypt_instance = MagicMock()
                mock_crypt_instance.hash.return_value = "hashed_securepassword"
                mock_crypt.return_value = mock_crypt_instance

                expected_user = User(
                    id=1,
                    username="newuser",
                    email="new@example.com",
                    hashed_password="hashed_securepassword",
                    avatar="http://gravatar.com/avatar/hash",
                    role=UserRole.USER,
                )
                user_service.repository.create_user = AsyncMock(
                    return_value=expected_user
                )

                result = await user_service.create_user(user_data)

                assert result.username == "newuser"
                assert result.email == "new@example.com"
                assert result.role == UserRole.USER
                assert result.avatar == "http://gravatar.com/avatar/hash"
                user_service.repository.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_admin_role(self, user_service):
        user_data = UserCreate(
            username="adminuser", email="admin@example.com", password="adminpassword"
        )

        with patch("src.services.users.Gravatar") as mock_gravatar_class:
            mock_gravatar = MagicMock()
            mock_gravatar.get_image.return_value = "http://gravatar.com/admin_hash"
            mock_gravatar_class.return_value = mock_gravatar

            with patch("src.services.users.CryptContext") as mock_crypt:
                mock_crypt_instance = MagicMock()
                mock_crypt_instance.hash.return_value = "hashed_adminpassword"
                mock_crypt.return_value = mock_crypt_instance

                expected_user = User(
                    id=2,
                    username="adminuser",
                    email="admin@example.com",
                    hashed_password="hashed_adminpassword",
                    avatar="http://gravatar.com/admin_hash",
                    role=UserRole.ADMIN,
                )
                user_service.repository.create_user = AsyncMock(
                    return_value=expected_user
                )

                result = await user_service.create_user(user_data, role=UserRole.ADMIN)

                assert result.username == "adminuser"
                assert result.email == "admin@example.com"
                assert result.role == UserRole.ADMIN
                assert result.avatar == "http://gravatar.com/admin_hash"
                user_service.repository.create_user.assert_called_once_with(
                    user_data, "http://gravatar.com/admin_hash", UserRole.ADMIN
                )

    @pytest.mark.asyncio
    async def test_create_user_gravatar_exception(self, user_service):
        user_data = UserCreate(
            username="noavataruser",
            email="noavatar@example.com",
            password="password123",
        )

        with patch("src.services.users.Gravatar") as mock_gravatar_class:
            mock_gravatar_class.side_effect = Exception("Gravatar service unavailable")

            with patch("src.services.users.CryptContext") as mock_crypt:
                mock_crypt_instance = MagicMock()
                mock_crypt_instance.hash.return_value = "hashed_password123"
                mock_crypt.return_value = mock_crypt_instance

                expected_user = User(
                    id=3,
                    username="noavataruser",
                    email="noavatar@example.com",
                    hashed_password="hashed_password123",
                    avatar=None,
                    role=UserRole.USER,
                )
                user_service.repository.create_user = AsyncMock(
                    return_value=expected_user
                )

                result = await user_service.create_user(user_data)
                assert result.username == "noavataruser"
                assert result.email == "noavatar@example.com"
                assert result.avatar is None
                user_service.repository.create_user.assert_called_once_with(
                    user_data, None, UserRole.USER
                )

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_service, sample_user):
        user_service.repository.get_user_by_id = AsyncMock(return_value=sample_user)

        result = await user_service.get_user_by_id(user_id=1)
        assert result == sample_user
        user_service.repository.get_user_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_service):
        user_service.repository.get_user_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await user_service.get_user_by_id(user_id=999)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"
        user_service.repository.get_user_by_id.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, user_service, sample_user):
        user_service.repository.get_user_by_username = AsyncMock(
            return_value=sample_user
        )

        result = await user_service.get_user_by_username(username="testuser")

        assert result == sample_user
        user_service.repository.get_user_by_username.assert_called_once_with("testuser")

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_service, sample_user):
        user_service.repository.get_user_by_email = AsyncMock(return_value=sample_user)
        result = await user_service.get_user_by_email(email="test@example.com")

        assert result == sample_user
        user_service.repository.get_user_by_email.assert_called_once_with(
            "test@example.com"
        )

    @pytest.mark.asyncio
    async def test_confirmed_email(self, user_service):
        user_service.repository.confirmed_email = AsyncMock()

        await user_service.confirmed_email("test@example.com")

        user_service.repository.confirmed_email.assert_called_once_with(
            "test@example.com"
        )

    @pytest.mark.asyncio
    async def test_update_avatar_url(self, user_service, sample_user):
        updated_user = User(
            id=sample_user.id,
            username=sample_user.username,
            email=sample_user.email,
            hashed_password=sample_user.hashed_password,
            confirmed=sample_user.confirmed,
            role=sample_user.role,
            avatar="http://example.com/new_avatar.png",
        )
        updated_user.avatar = "http://example.com/new_avatar.png"

        user_service.repository.update_avatar_url = AsyncMock(return_value=updated_user)

        result = await user_service.update_avatar_url(
            "test@example.com", "http://example.com/new_avatar.png"
        )

        assert result.avatar == "http://example.com/new_avatar.png"
        user_service.repository.update_avatar_url.assert_called_once_with(
            "test@example.com", "http://example.com/new_avatar.png"
        )

    @pytest.mark.asyncio
    async def test_update_password(self, user_service, sample_user):
        new_password = "newpassword123"
        updated_user = User(
            id=sample_user.id,
            username=sample_user.username,
            email=sample_user.email,
            hashed_password="hashed_newpassword123",
            confirmed=sample_user.confirmed,
            role=sample_user.role,
            avatar=sample_user.avatar,
        )

        with patch("src.services.users.CryptContext") as mock_crypt:
            mock_crypt_instance = MagicMock()
            mock_crypt_instance.hash.return_value = "hashed_newpassword123"
            mock_crypt.return_value = mock_crypt_instance

            user_service.repository.update_password = AsyncMock(
                return_value=updated_user
            )
            result = await user_service.update_password(
                "test@example.com", new_password
            )

            assert result.hashed_password == "hashed_newpassword123"
            user_service.repository.update_password.assert_called_once_with(
                "test@example.com", "hashed_newpassword123"
            )

    @pytest.mark.asyncio
    async def test_update_user_role(self, user_service, sample_user):
        updated_user = User(
            id=sample_user.id,
            username=sample_user.username,
            email=sample_user.email,
            hashed_password=sample_user.hashed_password,
            confirmed=sample_user.confirmed,
            role=UserRole.ADMIN,
            avatar=sample_user.avatar,
        )

        user_service.repository.update_user_role = AsyncMock(return_value=updated_user)

        result = await user_service.update_user_role("test@example.com", UserRole.ADMIN)

        assert result.role == UserRole.ADMIN
        user_service.repository.update_user_role.assert_called_once_with(
            "test@example.com", UserRole.ADMIN
        )


class TestUserServiceErrorHandling:

    @pytest.mark.asyncio
    async def test_update_avatar_url_user_not_found(self, user_service):
        user_service.repository.update_avatar_url = AsyncMock(
            side_effect=ValueError("User not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await user_service.update_avatar_url(
                "nonexistent@example.com", "http://example.com/avatar.png"
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_password_user_not_found(self, user_service):
        with patch("src.services.users.CryptContext") as mock_crypt:
            user_service.repository.update_password = AsyncMock(
                side_effect=ValueError("User not found")
            )

            with pytest.raises(HTTPException) as exc_info:
                await user_service.update_password(
                    "nonexistent@example.com", "newpassword"
                )

            assert exc_info.value.status_code == 404
            assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_user_role_user_not_found(self, user_service):
        user_service.repository.update_user_role = AsyncMock(
            side_effect=ValueError("User not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await user_service.update_user_role(
                "nonexistent@example.com", UserRole.ADMIN
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
