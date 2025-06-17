from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from src.repository.contacts import ContactRepository
from src.database.models import User
from schemas import ContactCreate, ContactUpdate


class ContactService:
    def __init__(self, db: AsyncSession):
        self.repository = ContactRepository(db)

    async def create_contact(self, body: ContactCreate, user: User):
        return await self.repository.create_contact(body, user)

    async def get_contacts(
        self, skip: int, limit: int, user: User, search: Optional[str] = None
    ):
        return await self.repository.get_contacts(skip, limit, user, search)

    async def get_contact(self, contact_id: int, user: User):
        return await self.repository.get_contact_by_id(contact_id, user)

    async def update_contact(self, contact_id: int, body: ContactUpdate, user: User):
        return await self.repository.update_contact(contact_id, body, user)

    async def remove_contact(self, contact_id: int, user: User):
        return await self.repository.remove_contact(contact_id, user)

    async def get_contacts_birthday_in_7_days(self, user: User):
        return await self.repository.get_contacts_birthday_in_7_days(user)
