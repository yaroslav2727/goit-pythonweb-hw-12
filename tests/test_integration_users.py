import asyncio
import pytest
from datetime import datetime, timedelta, UTC
from httpx import AsyncClient, ASGITransport
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch, MagicMock
from io import BytesIO

from main import app
from src.database.db import get_db
from src.database.redis_db import get_redis_cache
from src.database.models import Base, User, UserRole
from src.services.auth import Hash, create_access_token
from schemas import UserRole as SchemaUserRole


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
    echo=False,
)

async_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.get_event_loop_policy()


async def get_test_db():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_test_redis():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = None
    mock_redis.delete.return_value = None
    mock_redis.get_user.return_value = None
    mock_redis.set_user.return_value = None
    return mock_redis


@pytest.fixture(scope="function")
async def test_db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_user(test_db_session: AsyncSession):
    hash_handler = Hash()
    hashed_password = hash_handler.get_password_hash("testpassword123")

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password,
        confirmed=True,
        role=UserRole.USER,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(test_db_session: AsyncSession):
    hash_handler = Hash()
    hashed_password = hash_handler.get_password_hash("adminpassword123")

    user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=hashed_password,
        confirmed=True,
        role=UserRole.ADMIN,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    return user


@pytest.fixture
async def unconfirmed_admin_user(test_db_session: AsyncSession):
    hash_handler = Hash()
    hashed_password = hash_handler.get_password_hash("unconfirmedpassword123")

    user = User(
        username="unconfirmedadmin",
        email="unconfirmed@example.com",
        hashed_password=hashed_password,
        confirmed=False,
        role=UserRole.ADMIN,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    return user


@pytest.fixture
async def other_user(test_db_session: AsyncSession):
    hash_handler = Hash()
    hashed_password = hash_handler.get_password_hash("otherpassword123")

    user = User(
        username="otheruser",
        email="other@example.com",
        hashed_password=hashed_password,
        confirmed=True,
        role=UserRole.USER,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User):
    token_data = {"sub": test_user.username}
    access_token = create_access_token(data=token_data)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User):
    token_data = {"sub": admin_user.username}
    access_token = create_access_token(data=token_data)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def unconfirmed_admin_auth_headers(unconfirmed_admin_user: User):
    token_data = {"sub": unconfirmed_admin_user.username}
    access_token = create_access_token(data=token_data)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def client(test_db_session):
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_redis_cache] = get_test_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_image_file():
    content = b"fake image content"
    return BytesIO(content)


class TestUsersIntegration:

    async def test_get_me_success(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/users/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert data["confirmed"] == test_user.confirmed
        assert data["role"] == test_user.role.value

    async def test_get_me_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_me_invalid_token(self, client: AsyncClient):
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/users/me", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("src.services.upload_file.UploadFileService.upload_file")
    async def test_update_avatar_success(
        self,
        mock_upload,
        client: AsyncClient,
        admin_auth_headers: dict,
        admin_user: User,
    ):
        mock_upload.return_value = "https://example.com/new-avatar.jpg"

        files = {"file": ("test.jpg", b"fake image content", "image/jpeg")}

        response = await client.patch(
            "/api/users/avatar", files=files, headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == admin_user.id
        assert "avatar" in data
        mock_upload.assert_called_once()

    async def test_update_avatar_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        files = {"file": ("test.jpg", b"fake image content", "image/jpeg")}

        response = await client.patch(
            "/api/users/avatar", files=files, headers=auth_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_avatar_unconfirmed_admin(
        self, client: AsyncClient, unconfirmed_admin_auth_headers: dict
    ):
        files = {"file": ("test.jpg", b"fake image content", "image/jpeg")}

        response = await client.patch(
            "/api/users/avatar", files=files, headers=unconfirmed_admin_auth_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_avatar_unauthorized(self, client: AsyncClient):
        files = {"file": ("test.jpg", b"fake image content", "image/jpeg")}

        response = await client.patch("/api/users/avatar", files=files)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_update_avatar_no_file(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        response = await client.patch("/api/users/avatar", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("src.services.upload_file.UploadFileService.upload_file")
    async def test_update_avatar_upload_failure(
        self, mock_upload, client: AsyncClient, admin_auth_headers: dict
    ):
        mock_upload.side_effect = Exception("Upload failed")

        files = {"file": ("test.jpg", b"fake image content", "image/jpeg")}

        response = await client.patch(
            "/api/users/avatar", files=files, headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("libgravatar.Gravatar.get_image")
    async def test_delete_avatar_success(
        self,
        mock_gravatar,
        client: AsyncClient,
        admin_auth_headers: dict,
        admin_user: User,
    ):
        mock_gravatar.return_value = "https://gravatar.com/default-avatar.jpg"

        response = await client.delete("/api/users/avatar", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == admin_user.id
        assert "avatar" in data
        mock_gravatar.assert_called_once()

    async def test_delete_avatar_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.delete("/api/users/avatar", headers=auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_avatar_unauthorized(self, client: AsyncClient):
        response = await client.delete("/api/users/avatar")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("libgravatar.Gravatar.get_image")
    async def test_delete_avatar_gravatar_failure(
        self, mock_gravatar, client: AsyncClient, admin_auth_headers: dict
    ):
        mock_gravatar.side_effect = Exception("Gravatar failed")

        response = await client.delete("/api/users/avatar", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_update_user_role_success(
        self, client: AsyncClient, admin_auth_headers: dict, other_user: User
    ):
        role_data = {"email": other_user.email, "role": "admin"}

        response = await client.patch(
            "/api/users/role", json=role_data, headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == other_user.email
        assert data["role"] == "admin"

    async def test_update_user_role_non_admin(
        self, client: AsyncClient, auth_headers: dict, other_user: User
    ):
        role_data = {"email": other_user.email, "role": "admin"}

        response = await client.patch(
            "/api/users/role", json=role_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_user_role_unauthorized(
        self, client: AsyncClient, other_user: User
    ):
        role_data = {"email": other_user.email, "role": "admin"}

        response = await client.patch("/api/users/role", json=role_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_update_user_role_invalid_role(
        self, client: AsyncClient, admin_auth_headers: dict, other_user: User
    ):
        role_data = {"email": other_user.email, "role": "invalid_role"}

        response = await client.patch(
            "/api/users/role", json=role_data, headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_update_user_role_empty_data(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        response = await client.patch(
            "/api/users/role", json={}, headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_malformed_auth_token(self, client: AsyncClient):
        headers = {"Authorization": "InvalidFormat token"}

        response = await client.get("/api/users/me", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_bearer_token_missing_bearer_prefix(self, client: AsyncClient):
        headers = {"Authorization": "some_token"}

        response = await client.get("/api/users/me", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_me_with_avatar(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        test_db_session: AsyncSession,
    ):
        test_user.avatar = "https://example.com/avatar.jpg"
        await test_db_session.commit()

        response = await client.get("/api/users/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["avatar"] == "https://example.com/avatar.jpg"
