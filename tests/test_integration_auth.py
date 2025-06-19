import pytest
import asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport, Response
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch
from typing import Union

from main import app
from src.database.db import get_db
from src.database.redis_db import get_redis_cache
from src.database.models import Base, User, UserRole
from src.services.auth import (
    Hash,
    create_access_token,
    get_email_from_token,
    get_email_from_password_reset_token,
)


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
async def confirmed_user(test_db_session: AsyncSession):
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
async def unconfirmed_user(test_db_session: AsyncSession):
    hash_handler = Hash()
    hashed_password = hash_handler.get_password_hash("testpassword123")

    user = User(
        username="unconfirmeduser",
        email="unconfirmed@example.com",
        hashed_password=hashed_password,
        confirmed=False,
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
def auth_headers(confirmed_user: User):
    token_data = {"sub": confirmed_user.username}
    access_token = create_access_token(data=token_data)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User):
    token_data = {"sub": admin_user.username}
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


class TestAuthIntegration:

    async def test_register_user_success(self, client: AsyncClient):
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123",
        }

        with patch("src.api.auth.send_email") as mock_send_email:
            response = await client.post("/api/auth/register", json=user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["confirmed"] is False
        assert data["role"] == "user"
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_register_user_duplicate_email(
        self, client: AsyncClient, confirmed_user: User
    ):
        user_data = {
            "username": "differentuser",
            "email": confirmed_user.email,
            "password": "newpassword123",
        }

        response = await client.post("/api/auth/register", json=user_data)

        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_register_user_duplicate_username(
        self, client: AsyncClient, confirmed_user: User
    ):
        user_data = {
            "username": confirmed_user.username,
            "email": "different@example.com",
            "password": "newpassword123",
        }

        response = await client.post("/api/auth/register", json=user_data)

        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_register_user_invalid_email(self, client: AsyncClient):
        user_data = {
            "username": "newuser",
            "email": "invalid-email-format",
            "password": "newpassword123",
        }

        response = await client.post("/api/auth/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_register_user_missing_fields(self, client: AsyncClient):
        user_data = {
            "username": "newuser",
        }

        response = await client.post("/api/auth/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_register_admin_success(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        user_data = {
            "username": "newadmin",
            "email": "newadmin@example.com",
            "password": "adminpassword123",
        }

        with patch("src.api.auth.send_email") as mock_send_email:
            response = await client.post(
                "/api/auth/register-admin", json=user_data, headers=admin_auth_headers
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["confirmed"] is False
        assert data["role"] == "admin"

    async def test_register_admin_unauthorized(
        self, client: AsyncClient, auth_headers: dict
    ):
        user_data = {
            "username": "newadmin",
            "email": "newadmin@example.com",
            "password": "adminpassword123",
        }

        response = await client.post(
            "/api/auth/register-admin", json=user_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_register_admin_no_auth(self, client: AsyncClient):
        user_data = {
            "username": "newadmin",
            "email": "newadmin@example.com",
            "password": "adminpassword123",
        }

        response = await client.post("/api/auth/register-admin", json=user_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_success(self, client: AsyncClient, confirmed_user: User):
        login_data = {
            "username": confirmed_user.username,
            "password": "testpassword123",
        }

        response = await client.post(
            "/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    async def test_login_wrong_password(
        self, client: AsyncClient, confirmed_user: User
    ):
        login_data = {
            "username": confirmed_user.username,
            "password": "wrongpassword",
        }

        response = await client.post(
            "/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_nonexistent_user(self, client: AsyncClient):
        login_data = {
            "username": "nonexistentuser",
            "password": "somepassword",
        }

        response = await client.post(
            "/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_unconfirmed_user(
        self, client: AsyncClient, unconfirmed_user: User
    ):
        login_data = {
            "username": unconfirmed_user.username,
            "password": "testpassword123",
        }

        response = await client.post(
            "/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_missing_credentials(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/login",
            data={},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_confirmed_email_success(
        self, client: AsyncClient, unconfirmed_user: User
    ):
        token_data = {"sub": unconfirmed_user.email}
        token = create_access_token(data=token_data)

        response = await client.get(f"/api/auth/confirmed_email/{token}")

        assert response.status_code == status.HTTP_200_OK

    async def test_confirmed_email_invalid_token(self, client: AsyncClient):
        invalid_token = "invalid.token.here"

        response = await client.get(f"/api/auth/confirmed_email/{invalid_token}")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_confirmed_email_nonexistent_user(self, client: AsyncClient):
        token_data = {"sub": "nonexistent@example.com"}
        token = create_access_token(data=token_data)

        response = await client.get(f"/api/auth/confirmed_email/{token}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data["detail"].lower()

    async def test_request_email_existing_user(
        self, client: AsyncClient, unconfirmed_user: User
    ):
        email_data = {"email": unconfirmed_user.email}

        with patch("src.api.auth.send_email") as mock_send_email:
            response = await client.post("/api/auth/request_email", json=email_data)

        assert response.status_code == status.HTTP_200_OK

    async def test_request_email_nonexistent_user(self, client: AsyncClient):
        email_data = {"email": "nonexistent@example.com"}

        response = await client.post("/api/auth/request_email", json=email_data)

        assert response.status_code == status.HTTP_200_OK

    async def test_request_email_already_confirmed(
        self, client: AsyncClient, confirmed_user: User
    ):
        email_data = {"email": confirmed_user.email}

        response = await client.post("/api/auth/request_email", json=email_data)

        assert response.status_code == status.HTTP_200_OK

    async def test_request_email_invalid_format(self, client: AsyncClient):
        email_data = {"email": "invalid-email-format"}

        response = await client.post("/api/auth/request_email", json=email_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_request_password_reset_existing_user(
        self, client: AsyncClient, confirmed_user: User
    ):
        reset_data = {"email": confirmed_user.email}

        with patch("src.api.auth.send_password_reset_email") as mock_send_email:
            response = await client.post(
                "/api/auth/request-password-reset", json=reset_data
            )

        assert response.status_code == status.HTTP_200_OK

    async def test_request_password_reset_nonexistent_user(self, client: AsyncClient):
        reset_data = {"email": "nonexistent@example.com"}

        response = await client.post(
            "/api/auth/request-password-reset", json=reset_data
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_request_password_reset_invalid_email(self, client: AsyncClient):
        reset_data = {"email": "invalid-email-format"}

        response = await client.post(
            "/api/auth/request-password-reset", json=reset_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_confirm_password_reset_success(
        self, client: AsyncClient, confirmed_user: User
    ):
        token_data = {"sub": confirmed_user.email, "purpose": "password_reset"}
        token = create_access_token(data=token_data)

        reset_data = {
            "email": confirmed_user.email,
            "new_password": "newpassword123",
            "token": token,
        }

        with patch(
            "src.services.auth.get_email_from_password_reset_token",
            return_value=confirmed_user.email,
        ):
            response = await client.post(
                "/api/auth/confirm-password-reset", json=reset_data
            )

        assert response.status_code == status.HTTP_200_OK

    async def test_confirm_password_reset_invalid_token(
        self, client: AsyncClient, confirmed_user: User
    ):
        reset_data = {
            "email": confirmed_user.email,
            "new_password": "newpassword123",
            "token": "invalid.token.here",
        }

        response = await client.post(
            "/api/auth/confirm-password-reset", json=reset_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_confirm_password_reset_email_mismatch(
        self, client: AsyncClient, confirmed_user: User
    ):
        token_data = {"sub": "different@example.com", "purpose": "password_reset"}
        token = create_access_token(data=token_data)

        reset_data = {
            "email": confirmed_user.email,  # Different email than in token
            "new_password": "newpassword123",
            "token": token,
        }

        with patch(
            "src.services.auth.get_email_from_password_reset_token",
            return_value="different@example.com",
        ):
            response = await client.post(
                "/api/auth/confirm-password-reset", json=reset_data
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_confirm_password_reset_nonexistent_user(self, client: AsyncClient):
        token_data = {"sub": "nonexistent@example.com", "purpose": "password_reset"}
        token = create_access_token(data=token_data)

        reset_data = {
            "email": "nonexistent@example.com",
            "new_password": "newpassword123",
            "token": token,
        }

        with patch(
            "src.services.auth.get_email_from_password_reset_token",
            return_value="nonexistent@example.com",
        ):
            response = await client.post(
                "/api/auth/confirm-password-reset", json=reset_data
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()

    async def test_auth_field_validation(self, client: AsyncClient):
        long_username = "a" * 256
        user_data = {
            "username": long_username,
            "email": "test@example.com",
            "password": "password123",
        }

        response = await client.post("/api/auth/register", json=user_data)

        user_data = {
            "username": "validationtestuser",
            "email": "validationtest@example.com",
            "password": "",
        }

        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

        long_email = "a" * 200 + "@example.com"
        user_data = {
            "username": "validationtestuser2",
            "email": long_email,
            "password": "password123",
        }

        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_malformed_json_requests(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/register",
            content="invalid json content",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
