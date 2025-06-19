from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from src.repository.contacts import ContactRepository
from src.database.models import User
from schemas import ContactCreate, ContactUpdate


class ContactService:
    """Service class for contact-related operations.

    Provides high-level methods for contact management including creation,
    retrieval, updates, and deletion. Acts as a layer between API endpoints
    and repository operations.

    Attributes:
        repository (ContactRepository): The contact repository for database operations.
    """

    def __init__(self, db: AsyncSession):
        """Initialize ContactService with database session.

        Args:
            db (AsyncSession): SQLAlchemy async database session.
        """
        self.repository = ContactRepository(db)

    async def create_contact(self, body: ContactCreate, user: User):
        """Create a new contact for the user.

        Args:
            body (ContactCreate): Contact data to create.
            user (User): The user who owns the contact.

        Returns:
            Contact: The created contact object.
        """
        return await self.repository.create_contact(body, user)

    async def get_contacts(
        self, skip: int, limit: int, user: User, search: Optional[str] = None
    ):
        """Get contacts for the user with pagination and optional search.

        Args:
            skip (int): Number of records to skip for pagination.
            limit (int): Maximum number of records to return.
            user (User): The user whose contacts to retrieve.
            search (Optional[str]): Search term to filter contacts.

        Returns:
            List[Contact]: List of contacts matching the criteria.
        """
        return await self.repository.get_contacts(skip, limit, user, search)

    async def get_contact(self, contact_id: int, user: User):
        """Get a specific contact by ID for the user.

        Args:
            contact_id (int): The unique identifier of the contact.
            user (User): The user who should own the contact.

        Returns:
            Contact | None: The contact if found and belongs to user, None otherwise.
        """
        return await self.repository.get_contact_by_id(contact_id, user)

    async def update_contact(self, contact_id: int, body: ContactUpdate, user: User):
        """Update an existing contact for the user.

        Args:
            contact_id (int): The unique identifier of the contact to update.
            body (ContactUpdate): Partial contact data to update.
            user (User): The user who should own the contact.

        Returns:
            Contact | None: The updated contact if found and belongs to user, None otherwise.
        """
        return await self.repository.update_contact(contact_id, body, user)

    async def remove_contact(self, contact_id: int, user: User):
        """Remove a contact for the user.

        Args:
            contact_id (int): The unique identifier of the contact to remove.
            user (User): The user who should own the contact.

        Returns:
            Contact | None: The removed contact if found and belongs to user, None otherwise.
        """
        return await self.repository.remove_contact(contact_id, user)

    async def get_contacts_birthday_in_7_days(self, user: User):
        """Get contacts with upcoming birthdays within 7 days.

        Args:
            user (User): The user whose contacts to check for birthdays.

        Returns:
            List[Contact]: List of contacts with birthdays in the next 7 days.
        """
        return await self.repository.get_contacts_birthday_in_7_days(user)
