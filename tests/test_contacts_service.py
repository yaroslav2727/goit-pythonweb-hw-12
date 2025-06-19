import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.contacts import ContactService
from src.repository.contacts import ContactRepository
from src.database.models import User, Contact, UserRole
from schemas import ContactCreate, ContactUpdate
from datetime import datetime, timedelta


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def contact_service(mock_db):
    return ContactService(mock_db)


@pytest.fixture
def sample_user():
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        confirmed=True,
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


@pytest.fixture
def sample_contact():
    return Contact(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        birth_date=date(1990, 1, 15),
        additional_data="Software Engineer",
        user_id=1,
    )


@pytest.fixture
def sample_contacts():
    return [
        Contact(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1234567890",
            birth_date=date(1990, 1, 15),
            additional_data="Software Engineer",
            user_id=1,
        ),
        Contact(
            id=2,
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="+0987654321",
            birth_date=date(1985, 5, 20),
            additional_data="Designer",
            user_id=1,
        ),
        Contact(
            id=3,
            first_name="Bob",
            last_name="Johnson",
            email="bob.johnson@example.com",
            phone="+1122334455",
            birth_date=date(1975, 12, 10),
            additional_data="Manager",
            user_id=1,
        ),
    ]


@pytest.fixture
def contact_create_data():
    return ContactCreate(
        first_name="New",
        last_name="Contact",
        email="new.contact@example.com",
        phone="+1111111111",
        birth_date=date(1995, 3, 25),
        additional_data="Test Contact",
    )


@pytest.fixture
def contact_update_data():
    return ContactUpdate(
        first_name="Updated",
        last_name="Name",
        email="updated@example.com",
        phone="+2222222222",
    )


class TestContactService:

    def test_contact_service_initialization(self, contact_service, mock_db):
        assert contact_service.repository is not None
        assert isinstance(contact_service.repository, ContactRepository)

    @pytest.mark.asyncio
    async def test_create_contact(
        self, contact_service, contact_create_data, sample_user
    ):
        expected_contact = Contact(
            id=1,
            first_name="New",
            last_name="Contact",
            email="new.contact@example.com",
            phone="+1111111111",
            birth_date=date(1995, 3, 25),
            additional_data="Test Contact",
            user_id=1,
        )

        contact_service.repository.create_contact = AsyncMock(
            return_value=expected_contact
        )

        result = await contact_service.create_contact(contact_create_data, sample_user)

        assert result.first_name == "New"
        assert result.last_name == "Contact"
        assert result.email == "new.contact@example.com"
        assert result.phone == "+1111111111"
        assert result.birth_date == date(1995, 3, 25)
        assert result.additional_data == "Test Contact"
        assert result.user_id == 1
        contact_service.repository.create_contact.assert_called_once_with(
            contact_create_data, sample_user
        )

    @pytest.mark.asyncio
    async def test_get_contacts(self, contact_service, sample_contacts, sample_user):
        contact_service.repository.get_contacts = AsyncMock(
            return_value=sample_contacts
        )

        result = await contact_service.get_contacts(skip=0, limit=10, user=sample_user)

        assert len(result) == 3
        assert result[0].first_name == "John"
        assert result[1].first_name == "Jane"
        assert result[2].first_name == "Bob"
        contact_service.repository.get_contacts.assert_called_once_with(
            0, 10, sample_user, None
        )

    @pytest.mark.asyncio
    async def test_get_contacts_with_search(
        self, contact_service, sample_contacts, sample_user
    ):
        filtered_contacts = [sample_contacts[0]]

        contact_service.repository.get_contacts = AsyncMock(
            return_value=filtered_contacts
        )

        result = await contact_service.get_contacts(
            skip=0, limit=10, user=sample_user, search="John"
        )

        assert len(result) == 1
        assert result[0].first_name == "John"
        contact_service.repository.get_contacts.assert_called_once_with(
            0, 10, sample_user, "John"
        )

    @pytest.mark.asyncio
    async def test_get_contacts_pagination(
        self, contact_service, sample_contacts, sample_user
    ):
        filtered_contacts = sample_contacts[1:]

        contact_service.repository.get_contacts = AsyncMock(
            return_value=filtered_contacts
        )

        result = await contact_service.get_contacts(skip=1, limit=10, user=sample_user)

        assert len(result) == 2
        assert result[0].first_name == "Jane"
        assert result[1].first_name == "Bob"
        contact_service.repository.get_contacts.assert_called_once_with(
            1, 10, sample_user, None
        )
        contact_service.repository.get_contacts = AsyncMock(
            return_value=sample_contacts[1:]
        )

        result = await contact_service.get_contacts(skip=1, limit=5, user=sample_user)

        assert len(result) == 2
        assert result[0].first_name == "Jane"
        assert result[1].first_name == "Bob"
        contact_service.repository.get_contacts.assert_called_once_with(
            1, 5, sample_user, None
        )

    @pytest.mark.asyncio
    async def test_get_contact(self, contact_service, sample_contact, sample_user):
        contact_service.repository.get_contact_by_id = AsyncMock(
            return_value=sample_contact
        )

        result = await contact_service.get_contact(contact_id=1, user=sample_user)

        assert result == sample_contact
        assert result.id == 1
        assert result.first_name == "John"
        contact_service.repository.get_contact_by_id.assert_called_once_with(
            1, sample_user
        )

    @pytest.mark.asyncio
    async def test_get_contact_not_found(self, contact_service, sample_user):
        contact_service.repository.get_contact_by_id = AsyncMock(return_value=None)

        result = await contact_service.get_contact(contact_id=999, user=sample_user)

        assert result is None
        contact_service.repository.get_contact_by_id.assert_called_once_with(
            999, sample_user
        )

    @pytest.mark.asyncio
    async def test_update_contact(
        self, contact_service, contact_update_data, sample_contact, sample_user
    ):
        updated_contact = Contact(
            id=1,
            first_name="Updated",
            last_name="Name",
            email="updated@example.com",
            phone="+2222222222",
            birth_date=date(1990, 1, 15),  # Original birth_date
            additional_data="Software Engineer",  # Original additional_data
            user_id=1,
        )

        contact_service.repository.update_contact = AsyncMock(
            return_value=updated_contact
        )

        result = await contact_service.update_contact(
            contact_id=1, body=contact_update_data, user=sample_user
        )

        assert result.first_name == "Updated"
        assert result.last_name == "Name"
        assert result.email == "updated@example.com"
        assert result.phone == "+2222222222"
        assert result.id == 1
        contact_service.repository.update_contact.assert_called_once_with(
            1, contact_update_data, sample_user
        )

    @pytest.mark.asyncio
    async def test_update_contact_not_found(
        self, contact_service, contact_update_data, sample_user
    ):
        contact_service.repository.update_contact = AsyncMock(return_value=None)

        result = await contact_service.update_contact(
            contact_id=999, body=contact_update_data, user=sample_user
        )

        assert result is None
        contact_service.repository.update_contact.assert_called_once_with(
            999, contact_update_data, sample_user
        )

    @pytest.mark.asyncio
    async def test_remove_contact(self, contact_service, sample_contact, sample_user):
        contact_service.repository.remove_contact = AsyncMock(
            return_value=sample_contact
        )

        result = await contact_service.remove_contact(contact_id=1, user=sample_user)

        assert result == sample_contact
        assert result.id == 1
        contact_service.repository.remove_contact.assert_called_once_with(
            1, sample_user
        )

    @pytest.mark.asyncio
    async def test_remove_contact_not_found(self, contact_service, sample_user):
        contact_service.repository.remove_contact = AsyncMock(return_value=None)

        result = await contact_service.remove_contact(contact_id=999, user=sample_user)

        assert result is None
        contact_service.repository.remove_contact.assert_called_once_with(
            999, sample_user
        )

    @pytest.mark.asyncio
    async def test_get_contacts_birthday_in_7_days(self, contact_service, sample_user):
        today = datetime.now().date()
        birthday_date = today + timedelta(days=4)
        birthday_date2 = today + timedelta(days=2)

        upcoming_birthday_contacts = [
            Contact(
                id=1,
                first_name="Birthday",
                last_name="User1",
                email="birthday1@example.com",
                phone="+1111111111",
                birth_date=date(1990, birthday_date.month, birthday_date.day),
                additional_data="Birthday soon",
                user_id=1,
            ),
            Contact(
                id=2,
                first_name="Birthday",
                last_name="User2",
                email="birthday2@example.com",
                phone="+2222222222",
                birth_date=date(1985, birthday_date2.month, birthday_date2.day),
                additional_data="Birthday very soon",
                user_id=1,
            ),
        ]

        contact_service.repository.get_contacts_birthday_in_7_days = AsyncMock(
            return_value=upcoming_birthday_contacts
        )

        result = await contact_service.get_contacts_birthday_in_7_days(sample_user)

        assert len(result) == 2
        assert result[0].first_name == "Birthday"
        assert result[0].last_name == "User1"
        assert result[1].first_name == "Birthday"
        assert result[1].last_name == "User2"
        contact_service.repository.get_contacts_birthday_in_7_days.assert_called_once_with(
            sample_user
        )

    @pytest.mark.asyncio
    async def test_get_contacts_birthday_in_7_days_empty(
        self, contact_service, sample_user
    ):
        contact_service.repository.get_contacts_birthday_in_7_days = AsyncMock(
            return_value=[]
        )

        result = await contact_service.get_contacts_birthday_in_7_days(sample_user)

        assert len(result) == 0
        contact_service.repository.get_contacts_birthday_in_7_days.assert_called_once_with(
            sample_user
        )


class TestContactServiceWithDifferentUsers:

    @pytest.mark.asyncio
    async def test_operations_with_admin_user(
        self, contact_service, admin_user, contact_create_data
    ):
        expected_contact = Contact(
            id=1,
            first_name="New",
            last_name="Contact",
            email="new.contact@example.com",
            phone="+1111111111",
            birth_date=date(1995, 3, 25),
            additional_data="Test Contact",
            user_id=2,  # Admin user ID
        )

        contact_service.repository.create_contact = AsyncMock(
            return_value=expected_contact
        )

        result = await contact_service.create_contact(contact_create_data, admin_user)

        assert result.user_id == 2
        contact_service.repository.create_contact.assert_called_once_with(
            contact_create_data, admin_user
        )

    @pytest.mark.asyncio
    async def test_get_contacts_different_users(
        self, contact_service, sample_user, admin_user
    ):
        user_contacts = [
            Contact(
                id=1,
                first_name="User",
                last_name="Contact",
                email="user@example.com",
                phone="+1111111111",
                birth_date=date(1990, 1, 1),
                user_id=1,
            )
        ]
        admin_contacts = [
            Contact(
                id=2,
                first_name="Admin",
                last_name="Contact",
                email="admin@example.com",
                phone="+2222222222",
                birth_date=date(1985, 1, 1),
                user_id=2,
            )
        ]

        async def mock_get_contacts(skip, limit, user, search):
            if user.id == 1:
                return user_contacts
            elif user.id == 2:
                return admin_contacts
            return []

        contact_service.repository.get_contacts = AsyncMock(
            side_effect=mock_get_contacts
        )

        result_user = await contact_service.get_contacts(0, 10, sample_user)
        assert len(result_user) == 1
        assert result_user[0].first_name == "User"

        result_admin = await contact_service.get_contacts(0, 10, admin_user)
        assert len(result_admin) == 1
        assert result_admin[0].first_name == "Admin"


class TestContactServiceEdgeCases:

    @pytest.mark.asyncio
    async def test_create_contact_with_minimal_data(self, contact_service, sample_user):
        minimal_contact_data = ContactCreate(
            first_name="Min",
            last_name="Contact",
            email="min@example.com",
            phone="+0000000000",
            birth_date=date(2000, 1, 1),
            additional_data=None,  # Optional field
        )

        expected_contact = Contact(
            id=1,
            first_name="Min",
            last_name="Contact",
            email="min@example.com",
            phone="+0000000000",
            birth_date=date(2000, 1, 1),
            additional_data=None,
            user_id=1,
        )

        contact_service.repository.create_contact = AsyncMock(
            return_value=expected_contact
        )
        result = await contact_service.create_contact(minimal_contact_data, sample_user)
        assert result.additional_data is None
        assert result.first_name == "Min"
        contact_service.repository.create_contact.assert_called_once_with(
            minimal_contact_data, sample_user
        )

    @pytest.mark.asyncio
    async def test_update_contact_partial_update(self, contact_service, sample_user):
        partial_update = ContactUpdate(
            first_name="PartialUpdate", last_name=None, email=None, phone=None
        )

        updated_contact = Contact(
            id=1,
            first_name="PartialUpdate",
            last_name="Doe",  # Original value
            email="john.doe@example.com",  # Original value
            phone="+1234567890",  # Original value
            birth_date=date(1990, 1, 15),  # Original value
            additional_data="Software Engineer",  # Original value
            user_id=1,
        )

        contact_service.repository.update_contact = AsyncMock(
            return_value=updated_contact
        )

        result = await contact_service.update_contact(1, partial_update, sample_user)

        assert result.first_name == "PartialUpdate"
        assert result.last_name == "Doe"  # Unchanged
        contact_service.repository.update_contact.assert_called_once_with(
            1, partial_update, sample_user
        )

    @pytest.mark.asyncio
    async def test_get_contacts_with_zero_limit(self, contact_service, sample_user):
        contact_service.repository.get_contacts = AsyncMock(return_value=[])

        result = await contact_service.get_contacts(0, 0, sample_user)

        assert len(result) == 0
        contact_service.repository.get_contacts.assert_called_once_with(
            0, 0, sample_user, None
        )

    @pytest.mark.asyncio
    async def test_get_contacts_with_large_skip(self, contact_service, sample_user):
        contact_service.repository.get_contacts = AsyncMock(return_value=[])

        result = await contact_service.get_contacts(1000, 10, sample_user)

        assert len(result) == 0
        contact_service.repository.get_contacts.assert_called_once_with(
            1000, 10, sample_user, None
        )
