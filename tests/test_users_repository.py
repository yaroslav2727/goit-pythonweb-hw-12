import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, UserRole
from src.repository.users import UserRepository
from schemas import UserCreate


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def user_repository(mock_session):
    return UserRepository(mock_session)


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


class TestUserRepository:

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_repository, mock_session, sample_user):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.get_user_by_id(user_id=1)

        assert result is not None
        assert result.id == 1
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        assert result.role == UserRole.USER
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.get_user_by_id(user_id=999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_username(
        self, user_repository, mock_session, sample_user
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.get_user_by_username(username="testuser")

        assert result is not None
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        assert result.role == UserRole.USER
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, user_repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.get_user_by_username(username="nonexistent")

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_repository, mock_session, sample_user):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.get_user_by_email(email="test@example.com")

        assert result is not None
        assert result.email == "test@example.com"
        assert result.username == "testuser"
        assert result.role == UserRole.USER
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.get_user_by_email(
            email="nonexistent@example.com"
        )

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_default_role(self, user_repository, mock_session):
        user_data = UserCreate(
            username="newuser", email="new@example.com", password="securepassword"
        )

        result = await user_repository.create_user(
            body=user_data, avatar="http://example.com/avatar.png"
        )

        assert isinstance(result, User)
        assert result.username == "newuser"
        assert result.email == "new@example.com"
        assert result.hashed_password == "securepassword"
        assert result.avatar == "http://example.com/avatar.png"
        assert result.role == UserRole.USER  # Default role

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(result)

    @pytest.mark.asyncio
    async def test_create_user_admin_role(self, user_repository, mock_session):
        user_data = UserCreate(
            username="adminuser", email="admin@example.com", password="adminpassword"
        )

        result = await user_repository.create_user(
            body=user_data,
            avatar="http://example.com/admin_avatar.png",
            role=UserRole.ADMIN,
        )

        assert isinstance(result, User)
        assert result.username == "adminuser"
        assert result.email == "admin@example.com"
        assert result.hashed_password == "adminpassword"
        assert result.avatar == "http://example.com/admin_avatar.png"
        assert result.role == UserRole.ADMIN

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(result)

    @pytest.mark.asyncio
    async def test_create_user_without_avatar(self, user_repository, mock_session):
        user_data = UserCreate(
            username="noavataruser",
            email="noavatar@example.com",
            password="password123",
        )

        result = await user_repository.create_user(body=user_data)

        assert isinstance(result, User)
        assert result.username == "noavataruser"
        assert result.email == "noavatar@example.com"
        assert result.avatar is None
        assert result.role == UserRole.USER

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(result)

    @pytest.mark.asyncio
    async def test_confirmed_email(self, user_repository, mock_session, sample_user):
        assert sample_user.confirmed is False

        user_repository.get_user_by_email = AsyncMock(return_value=sample_user)

        await user_repository.confirmed_email("test@example.com")

        assert sample_user.confirmed is True
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_confirmed_email_user_not_found(self, user_repository, mock_session):
        user_repository.get_user_by_email = AsyncMock(return_value=None)

        await user_repository.confirmed_email("nonexistent@example.com")

        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_avatar_url(self, user_repository, mock_session, sample_user):
        original_avatar = sample_user.avatar
        new_avatar_url = "http://example.com/new_avatar.png"

        user_repository.get_user_by_email = AsyncMock(return_value=sample_user)

        updated_user = await user_repository.update_avatar_url(
            "test@example.com", new_avatar_url
        )

        assert updated_user.avatar == new_avatar_url
        assert updated_user.avatar != original_avatar
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(sample_user)

    @pytest.mark.asyncio
    async def test_update_avatar_url_user_not_found(
        self, user_repository, mock_session
    ):
        user_repository.get_user_by_email = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="User not found"):
            await user_repository.update_avatar_url(
                "nonexistent@example.com", "http://example.com/avatar.png"
            )

        mock_session.commit.assert_not_awaited()
        mock_session.refresh.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_password(self, user_repository, mock_session, sample_user):
        original_password = sample_user.hashed_password
        new_password_hash = "new_hashed_password"

        user_repository.get_user_by_email = AsyncMock(return_value=sample_user)

        updated_user = await user_repository.update_password(
            "test@example.com", new_password_hash
        )

        assert updated_user.hashed_password == new_password_hash
        assert updated_user.hashed_password != original_password
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(sample_user)

    @pytest.mark.asyncio
    async def test_update_password_user_not_found(self, user_repository, mock_session):
        user_repository.get_user_by_email = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="User not found"):
            await user_repository.update_password(
                "nonexistent@example.com", "new_password_hash"
            )

        mock_session.commit.assert_not_awaited()
        mock_session.refresh.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_user_role(self, user_repository, mock_session, sample_user):
        assert sample_user.role == UserRole.USER  # Initial role

        user_repository.get_user_by_email = AsyncMock(return_value=sample_user)

        updated_user = await user_repository.update_user_role(
            "test@example.com", UserRole.ADMIN
        )

        assert updated_user.role == UserRole.ADMIN
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(sample_user)

    @pytest.mark.asyncio
    async def test_update_user_role_user_not_found(self, user_repository, mock_session):
        user_repository.get_user_by_email = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="User not found"):
            await user_repository.update_user_role(
                "nonexistent@example.com", UserRole.ADMIN
            )

        mock_session.commit.assert_not_awaited()
        mock_session.refresh.assert_not_awaited()


class TestUserRepositoryEdgeCases:

    @pytest.mark.asyncio
    async def test_create_user_with_special_characters(
        self, user_repository, mock_session
    ):
        user_data = UserCreate(
            username="user_with.special-chars",
            email="user+test@sub-domain.example.com",
            password="complex_password!@#$",
        )

        result = await user_repository.create_user(body=user_data)

        assert isinstance(result, User)
        assert result.username == "user_with.special-chars"
        assert result.email == "user+test@sub-domain.example.com"
        assert result.hashed_password == "complex_password!@#$"

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(result)

    @pytest.mark.asyncio
    async def test_update_avatar_url_empty_string(
        self, user_repository, mock_session, sample_user
    ):
        user_repository.get_user_by_email = AsyncMock(return_value=sample_user)

        updated_user = await user_repository.update_avatar_url("test@example.com", "")

        assert updated_user.avatar == ""
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(sample_user)

    @pytest.mark.asyncio
    async def test_multiple_operations_same_user(
        self, user_repository, mock_session, sample_user
    ):
        user_repository.get_user_by_email = AsyncMock(return_value=sample_user)

        await user_repository.confirmed_email("test@example.com")
        await user_repository.update_avatar_url("test@example.com", "new_avatar.png")
        await user_repository.update_user_role("test@example.com", UserRole.ADMIN)

        assert sample_user.confirmed is True
        assert sample_user.avatar == "new_avatar.png"
        assert sample_user.role == UserRole.ADMIN

        assert mock_session.commit.await_count == 3
        assert mock_session.refresh.await_count == 2
