import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date

from src.database.models import Contact, User, UserRole
from src.repository.contacts import ContactRepository
from schemas import ContactCreate, ContactUpdate


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def contact_repository(mock_session):
    return ContactRepository(mock_session)


@pytest.fixture
def user():
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        confirmed=True,
        role=UserRole.USER,
    )


@pytest.fixture
def sample_contact(user):
    return Contact(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        birth_date=date(1990, 1, 15),
        additional_data="Test contact",
        user_id=user.id,
        user=user,
    )


@pytest.fixture
def sample_contacts(user):
    return [
        Contact(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1234567890",
            birth_date=date(1990, 1, 15),
            user_id=user.id,
            user=user,
        ),
        Contact(
            id=2,
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="+0987654321",
            birth_date=date(1985, 5, 20),
            user_id=user.id,
            user=user,
        ),
    ]


class TestContactRepository:

    @pytest.mark.asyncio
    async def test_get_contacts(
        self, contact_repository, mock_session, user, sample_contacts
    ):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_contacts
        mock_session.execute = AsyncMock(return_value=mock_result)

        contacts = await contact_repository.get_contacts(skip=0, limit=10, user=user)

        assert len(contacts) == 2
        assert contacts[0].first_name == "John"
        assert contacts[0].last_name == "Doe"
        assert contacts[1].first_name == "Jane"
        assert contacts[1].last_name == "Smith"

    @pytest.mark.asyncio
    async def test_get_contacts_with_search(
        self, contact_repository, mock_session, user, sample_contacts
    ):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_contacts[0]]
        mock_session.execute = AsyncMock(return_value=mock_result)

        contacts = await contact_repository.get_contacts(
            skip=0, limit=10, user=user, search="John"
        )

        assert len(contacts) == 1
        assert contacts[0].first_name == "John"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contact_by_id(
        self, contact_repository, mock_session, user, sample_contact
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_contact
        mock_session.execute = AsyncMock(return_value=mock_result)

        contact = await contact_repository.get_contact_by_id(contact_id=1, user=user)

        assert contact is not None
        assert contact.id == 1
        assert contact.first_name == "John"
        assert contact.last_name == "Doe"
        assert contact.email == "john.doe@example.com"

    @pytest.mark.asyncio
    async def test_get_contact_by_id_not_found(
        self, contact_repository, mock_session, user
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        contact = await contact_repository.get_contact_by_id(contact_id=999, user=user)

        assert contact is None

    @pytest.mark.asyncio
    async def test_create_contact(self, contact_repository, mock_session, user):
        contact_data = ContactCreate(
            first_name="Alice",
            last_name="Johnson",
            email="alice.johnson@example.com",
            phone="+5555555555",
            birth_date=date(1992, 3, 10),
            additional_data="New contact",
        )

        result = await contact_repository.create_contact(body=contact_data, user=user)

        assert isinstance(result, Contact)
        assert result.first_name == "Alice"
        assert result.last_name == "Johnson"
        assert result.email == "alice.johnson@example.com"
        assert result.phone == "+5555555555"
        assert result.birth_date == date(1992, 3, 10)
        assert result.additional_data == "New contact"
        assert result.user_id == user.id

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(result)

    @pytest.mark.asyncio
    async def test_update_contact(
        self, contact_repository, mock_session, user, sample_contact
    ):
        contact_data = ContactUpdate.model_validate(
            {
                "first_name": "John Updated",
                "last_name": "Doe Updated",
                "email": "john.updated@example.com",
            }
        )

        contact_repository.get_contact_by_id = AsyncMock(return_value=sample_contact)

        result = await contact_repository.update_contact(
            contact_id=1, body=contact_data, user=user
        )

        assert result is not None
        assert sample_contact.first_name == "John Updated"
        assert sample_contact.last_name == "Doe Updated"
        assert sample_contact.email == "john.updated@example.com"

        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(sample_contact)

    @pytest.mark.asyncio
    async def test_update_contact_partial(
        self, contact_repository, mock_session, user, sample_contact
    ):
        original_email = sample_contact.email
        contact_data = ContactUpdate.model_validate({"first_name": "John Updated"})

        contact_repository.get_contact_by_id = AsyncMock(return_value=sample_contact)

        result = await contact_repository.update_contact(
            contact_id=1, body=contact_data, user=user
        )

        assert result is not None
        assert sample_contact.first_name == "John Updated"
        assert sample_contact.email == original_email

        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(sample_contact)

    @pytest.mark.asyncio
    async def test_update_contact_not_found(
        self, contact_repository, mock_session, user
    ):
        contact_data = ContactUpdate.model_validate({"first_name": "Updated Name"})

        contact_repository.get_contact_by_id = AsyncMock(return_value=None)

        result = await contact_repository.update_contact(
            contact_id=999, body=contact_data, user=user
        )

        assert result is None
        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_remove_contact(
        self, contact_repository, mock_session, user, sample_contact
    ):
        contact_repository.get_contact_by_id = AsyncMock(return_value=sample_contact)

        result = await contact_repository.remove_contact(contact_id=1, user=user)

        assert result is not None
        assert result.first_name == "John"
        assert result.last_name == "Doe"

        mock_session.delete.assert_awaited_once_with(sample_contact)
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_remove_contact_not_found(
        self, contact_repository, mock_session, user
    ):
        contact_repository.get_contact_by_id = AsyncMock(return_value=None)

        result = await contact_repository.remove_contact(contact_id=999, user=user)

        assert result is None
        mock_session.delete.assert_not_awaited()
        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_contacts_birthday_in_7_days(
        self, contact_repository, mock_session, user
    ):
        today = date.today()
        upcoming_birthday = today + timedelta(days=3)

        birthday_contact = Contact(
            id=1,
            first_name="Birthday",
            last_name="Person",
            email="birthday@example.com",
            phone="+1111111111",
            birth_date=upcoming_birthday.replace(
                year=1990
            ),  # Same month/day, different year
            user_id=user.id,
            user=user,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [birthday_contact]
        mock_session.execute = AsyncMock(return_value=mock_result)

        contacts = await contact_repository.get_contacts_birthday_in_7_days(user=user)

        assert len(contacts) == 1
        assert contacts[0].first_name == "Birthday"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contacts_birthday_in_7_days_empty(
        self, contact_repository, mock_session, user
    ):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        contacts = await contact_repository.get_contacts_birthday_in_7_days(user=user)

        assert len(contacts) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contacts_empty_result(
        self, contact_repository, mock_session, user
    ):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        contacts = await contact_repository.get_contacts(skip=0, limit=10, user=user)

        assert len(contacts) == 0
        assert isinstance(contacts, list)
