from typing import List, Optional

from sqlalchemy import select, or_, extract, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from schemas import ContactCreate, ContactUpdate, ContactResponse
from datetime import date, timedelta


class ContactRepository:
    """Repository class for contact database operations.

    Provides low-level database operations for contact entities including
    CRUD operations, search functionality, and birthday queries.

    Attributes:
        db (AsyncSession): SQLAlchemy async database session.
    """

    def __init__(self, session: AsyncSession):
        """Initialize ContactRepository with database session.

        Args:
            session (AsyncSession): SQLAlchemy async database session.
        """
        self.db = session

    async def get_contacts(
        self, skip: int, limit: int, user: User, search: Optional[str] = None
    ) -> List[Contact]:
        """Retrieve contacts for a user with pagination and optional search.

        Args:
            skip (int): Number of records to skip for pagination.
            limit (int): Maximum number of records to return.
            user (User): The user whose contacts to retrieve.
            search (Optional[str]): Search term to filter by name or email.

        Returns:
            List[Contact]: List of contacts matching the criteria.
        """
        stmt = select(Contact).filter_by(user_id=user.id)

        if search:
            search_filter = or_(
                Contact.first_name.like(f"%{search}%"),
                Contact.last_name.like(f"%{search}%"),
                Contact.email.like(f"%{search}%"),
            )
            stmt = stmt.where(search_filter)

        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        """Retrieve a specific contact by ID for a user.

        Args:
            contact_id (int): The unique identifier of the contact.
            user (User): The user who should own the contact.

        Returns:
            Contact | None: The contact if found and belongs to user, None otherwise.
        """
        stmt = select(Contact).filter_by(id=contact_id, user_id=user.id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_contact(self, body: ContactCreate, user: User) -> Contact:
        """Create a new contact for a user.

        Args:
            body (ContactCreate): Contact data to create.
            user (User): The user who will own the contact.

        Returns:
            Contact: The created contact object with assigned ID.
        """
        contact = Contact(**body.model_dump(exclude_unset=True), user_id=user.id)
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def update_contact(
        self, contact_id: int, body: ContactUpdate, user: User
    ) -> Contact | None:
        """Update an existing contact for a user.

        Args:
            contact_id (int): The unique identifier of the contact to update.
            body (ContactUpdate): Partial contact data to update.
            user (User): The user who should own the contact.

        Returns:
            Contact | None: The updated contact if found and belongs to user, None otherwise.
        """
        contact = await self.get_contact_by_id(contact_id, user)

        if contact:
            if body.first_name is not None:
                contact.first_name = body.first_name
            if body.last_name is not None:
                contact.last_name = body.last_name
            if body.email is not None:
                contact.email = body.email
            if body.phone is not None:
                contact.phone = body.phone
            if body.birth_date is not None:
                contact.birth_date = body.birth_date
            if body.additional_data is not None:
                contact.additional_data = body.additional_data

            await self.db.commit()
            await self.db.refresh(contact)

        return contact

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        """Remove a contact for a user.

        Args:
            contact_id (int): The unique identifier of the contact to remove.
            user (User): The user who should own the contact.

        Returns:
            Contact | None: The removed contact if found and belongs to user, None otherwise.
        """
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            await self.db.delete(contact)
            await self.db.commit()
        return contact

    async def get_contacts_birthday_in_7_days(self, user: User) -> List[Contact]:
        """Get contacts with birthdays in the next 7 days.

        Retrieves contacts belonging to the user whose birthdays fall
        within the next 7 days from today.

        Args:
            user (User): The user whose contacts to check for birthdays.

        Returns:
            List[Contact]: List of contacts with upcoming birthdays.
        """
        today = date.today()

        upcoming_dates = []
        for i in range(7):
            next_date = today + timedelta(days=i)
            upcoming_dates.append((next_date.month, next_date.day))

        date_conditions = []
        for month, day in upcoming_dates:
            date_conditions.append(
                and_(
                    extract("month", Contact.birth_date) == month,
                    extract("day", Contact.birth_date) == day,
                )
            )

        stmt = (
            select(Contact)
            .filter(Contact.user_id == user.id)
            .filter(or_(*date_conditions))
            .order_by(
                extract("month", Contact.birth_date), extract("day", Contact.birth_date)
            )
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
