import pytest
import asyncio
from datetime import date, datetime, timedelta
from httpx import AsyncClient, ASGITransport, Response
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock
from typing import Union

from main import app
from src.database.db import get_db
from src.database.redis_db import get_redis_cache
from src.database.models import Base, User, Contact, UserRole
from src.services.auth import Hash, create_access_token


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
async def test_contact(test_db_session: AsyncSession, test_user: User):
    contact = Contact(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1-555-0123",
        birth_date=date(1990, 5, 15),
        additional_data="Test contact",
        user_id=test_user.id,
    )
    test_db_session.add(contact)
    await test_db_session.commit()
    await test_db_session.refresh(contact)
    return contact


@pytest.fixture
async def multiple_test_contacts(test_db_session: AsyncSession, test_user: User):
    contacts = [
        Contact(
            first_name="Alice",
            last_name="Smith",
            email="alice.smith@example.com",
            phone="+1-555-0101",
            birth_date=date(1985, 3, 20),
            additional_data="Alice's contact",
            user_id=test_user.id,
        ),
        Contact(
            first_name="Bob",
            last_name="Johnson",
            email="bob.johnson@example.com",
            phone="+1-555-0102",
            birth_date=date(1992, 8, 10),
            additional_data="Bob's contact",
            user_id=test_user.id,
        ),
        Contact(
            first_name="Charlie",
            last_name="Brown",
            email="charlie.brown@example.com",
            phone="+1-555-0103",
            birth_date=date(1988, 12, 25),
            additional_data="Charlie's contact",
            user_id=test_user.id,
        ),
    ]

    for contact in contacts:
        test_db_session.add(contact)
    await test_db_session.commit()

    for contact in contacts:
        await test_db_session.refresh(contact)

    return contacts


@pytest.fixture
async def upcoming_birthday_contacts(test_db_session: AsyncSession, test_user: User):
    today = date.today()

    def safe_date(base_date, year=1990):
        try:
            return date(year, base_date.month, base_date.day)
        except ValueError:
            return date(year, base_date.month, base_date.day - 1)

    contacts = [
        Contact(
            first_name="Birthday",
            last_name="Today",
            email="birthday.today@example.com",
            phone="+1-555-0201",
            birth_date=safe_date(today),
            user_id=test_user.id,
        ),
        Contact(
            first_name="Birthday",
            last_name="Tomorrow",
            email="birthday.tomorrow@example.com",
            phone="+1-555-0202",
            birth_date=safe_date(today + timedelta(days=1)),
            user_id=test_user.id,
        ),
        Contact(
            first_name="Birthday",
            last_name="NextWeek",
            email="birthday.nextweek@example.com",
            phone="+1-555-0203",
            birth_date=safe_date(today + timedelta(days=6)),
            user_id=test_user.id,
        ),
        Contact(
            first_name="Birthday",
            last_name="TooFar",
            email="birthday.toofar@example.com",
            phone="+1-555-0204",
            birth_date=safe_date(today + timedelta(days=10)),
            user_id=test_user.id,
        ),
    ]

    for contact in contacts:
        test_db_session.add(contact)
    await test_db_session.commit()

    for contact in contacts:
        await test_db_session.refresh(contact)

    return contacts


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
async def client(test_db_session):
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_redis_cache] = get_test_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


class TestContactsIntegration:

    async def test_create_contact_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        contact_data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane.doe@example.com",
            "phone": "+1-555-0124",
            "birth_date": "1995-07-22",
            "additional_data": "New contact",
        }

        response = await client.post(
            "/api/contacts/", json=contact_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["first_name"] == contact_data["first_name"]
        assert data["last_name"] == contact_data["last_name"]
        assert data["email"] == contact_data["email"]
        assert data["phone"] == contact_data["phone"]
        assert data["birth_date"] == contact_data["birth_date"]
        assert data["additional_data"] == contact_data["additional_data"]
        assert "id" in data
        assert "user_id" in data

    async def test_create_contact_unauthorized(self, client: AsyncClient):
        contact_data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane.doe@example.com",
            "phone": "+1-555-0124",
            "birth_date": "1995-07-22",
        }

        response = await client.post("/api/contacts/", json=contact_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_contact_invalid_data(
        self, client: AsyncClient, auth_headers: dict
    ):
        contact_data = {
            "first_name": "",  # Empty
            "last_name": "Doe",
            "email": "invalid-email",  # Invalid email
            "phone": "+1-555-0124",
            "birth_date": "invalid-date",  # Invalid date
        }

        response = await client.post(
            "/api/contacts/", json=contact_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_contacts_empty_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get("/api/contacts/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_get_contact_by_id_success(
        self, client: AsyncClient, auth_headers: dict, test_contact: Contact
    ):
        response = await client.get(
            f"/api/contacts/{test_contact.id}", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_contact.id
        assert data["first_name"] == test_contact.first_name
        assert data["last_name"] == test_contact.last_name
        assert data["email"] == test_contact.email

    async def test_get_contact_by_id_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get("/api/contacts/999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_contact_unauthorized(
        self, client: AsyncClient, test_contact: Contact
    ):
        response = await client.get(f"/api/contacts/{test_contact.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_update_contact_success(
        self, client: AsyncClient, auth_headers: dict, test_contact: Contact
    ):
        update_data = {"first_name": "Johnny", "phone": "+1-555-9999"}

        response = await client.patch(
            f"/api/contacts/{test_contact.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["first_name"] == "Johnny"
        assert data["phone"] == "+1-555-9999"
        assert data["last_name"] == test_contact.last_name  # Unchanged
        assert data["email"] == test_contact.email  # Unchanged

    async def test_update_contact_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        update_data = {"first_name": "Johnny"}

        response = await client.patch(
            "/api/contacts/999", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_contact_invalid_data(
        self, client: AsyncClient, auth_headers: dict, test_contact: Contact
    ):
        update_data = {"email": "invalid-email-format"}

        response = await client.patch(
            f"/api/contacts/{test_contact.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_delete_contact_success(
        self, client: AsyncClient, auth_headers: dict, test_contact: Contact
    ):
        response = await client.delete(
            f"/api/contacts/{test_contact.id}", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_contact.id

        get_response = await client.get(
            f"/api/contacts/{test_contact.id}", headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_contact_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.delete("/api/contacts/999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_search_no_results(
        self, client: AsyncClient, auth_headers: dict, multiple_test_contacts: list
    ):
        response = await client.get(
            "/api/contacts/?search=nonexistent", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0

    async def test_update_contact_empty_fields(
        self, client: AsyncClient, auth_headers: dict, test_contact: Contact
    ):
        update_data = {"additional_data": ""}  # Empty string instead of None

        response = await client.patch(
            f"/api/contacts/{test_contact.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["additional_data"] == ""

    async def test_invalid_contact_id_formats(
        self, client: AsyncClient, auth_headers: dict
    ):
        invalid_ids = [
            "abc",
            "0",
            "-1",
        ]

        for invalid_id in invalid_ids:

            response = await client.get(
                f"/api/contacts/{invalid_id}", headers=auth_headers
            )
            assert response.status_code in [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

            response = await client.patch(
                f"/api/contacts/{invalid_id}",
                json={"first_name": "Test"},
                headers=auth_headers,
            )
            assert response.status_code in [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

            response = await client.delete(
                f"/api/contacts/{invalid_id}", headers=auth_headers
            )
            assert response.status_code in [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    async def test_malformed_auth_token(self, client: AsyncClient):
        malformed_headers = [
            {"Authorization": "Bearer invalid_token"},
            {"Authorization": "InvalidFormat token"},
            {"Authorization": "Bearer "},
            {"Authorization": ""},
        ]

        for headers in malformed_headers:
            response = await client.get("/api/contacts/", headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_expired_token_simulation(self, client: AsyncClient, test_user: User):
        token_data = {"sub": test_user.username}
        expired_token = create_access_token(data=token_data, expires_delta=1)

        import time

        time.sleep(2)

        expired_headers = {"Authorization": f"Bearer {expired_token}"}

        response = await client.get("/api/contacts/", headers=expired_headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
