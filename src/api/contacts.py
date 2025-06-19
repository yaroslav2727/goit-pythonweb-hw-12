from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from schemas import ContactBase, ContactCreate, ContactUpdate, ContactResponse
from src.database.models import User
from src.services.auth import get_current_user
from src.services.contacts import ContactService


router = APIRouter(prefix="/contacts", tags=["contacts"])


# Створити новий контакт
@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new contact for the authenticated user.

    Creates a new contact record with the provided contact information.
    The contact will be associated with the currently authenticated user.

    Args:
        body (ContactCreate): Contact data including name, email, phone, and birth date.
        db (AsyncSession): Database session dependency.
        user (User): Currently authenticated user.

    Returns:
        ContactResponse: The created contact object with generated ID.
    """
    contact_service = ContactService(db)
    return await contact_service.create_contact(body, user)


# Отримати список всіх контактів
@router.get("/", response_model=List[ContactResponse])
async def read_contacts(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get list of contacts for the authenticated user.

    Retrieves contacts belonging to the authenticated user with optional
    pagination and search functionality.

    Args:
        skip (int): Number of records to skip for pagination. Defaults to 0.
        limit (int): Maximum number of records to return. Defaults to 100.
        search (Optional[str]): Search term to filter contacts by name or email.
        db (AsyncSession): Database session dependency.
        user (User): Currently authenticated user.

    Returns:
        List[ContactResponse]: List of contact objects matching the criteria.
    """
    contact_service = ContactService(db)
    contacts = await contact_service.get_contacts(skip, limit, user, search)
    return contacts


# Отримати контакти, у яких день народження протягом тижня
@router.get("/upcoming-birthdays", response_model=List[ContactResponse])
async def get_upcoming_birthdays(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Get contacts with upcoming birthdays within 7 days.

    Retrieves all contacts belonging to the authenticated user whose birthdays
    occur within the next 7 days from today.

    Args:
        db (AsyncSession): Database session dependency.
        user (User): Currently authenticated user.

    Returns:
        List[ContactResponse]: List of contacts with upcoming birthdays.
    """
    contact_service = ContactService(db)
    contacts = await contact_service.get_contacts_birthday_in_7_days(user)
    return contacts


# Отримати один контакт за ідентифікатором
@router.get("/{contact_id}", response_model=ContactResponse)
async def read_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific contact by ID.

    Retrieves a single contact by its ID. The contact must belong to the
    authenticated user.

    Args:
        contact_id (int): The unique identifier of the contact.
        db (AsyncSession): Database session dependency.
        user (User): Currently authenticated user.

    Returns:
        ContactResponse: The requested contact object.

    Raises:
        HTTPException: 404 Not Found if contact doesn't exist or doesn't belong to user.
    """
    contact_service = ContactService(db)
    contact = await contact_service.get_contact(contact_id, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact


# Оновити контакт, що існує
@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    body: ContactUpdate,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update an existing contact.

    Updates contact information with the provided data. Only the fields
    included in the request body will be updated. The contact must belong
    to the authenticated user.

    Args:
        body (ContactUpdate): Partial contact data to update.
        contact_id (int): The unique identifier of the contact to update.
        db (AsyncSession): Database session dependency.
        user (User): Currently authenticated user.

    Returns:
        ContactResponse: The updated contact object.

    Raises:
        HTTPException: 404 Not Found if contact doesn't exist or doesn't belong to user.
    """
    contact_service = ContactService(db)
    contact = await contact_service.update_contact(contact_id, body, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact


# Видалити контакт
@router.delete("/{contact_id}", response_model=ContactResponse)
async def remove_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a specific contact.

    Permanently deletes a contact from the database. The contact must belong
    to the authenticated user.

    Args:
        contact_id (int): The unique identifier of the contact to delete.
        db (AsyncSession): Database session dependency.
        user (User): Currently authenticated user.

    Returns:
        ContactResponse: The deleted contact object.

    Raises:
        HTTPException: 404 Not Found if contact doesn't exist or doesn't belong to user.
    """
    contact_service = ContactService(db)
    contact = await contact_service.remove_contact(contact_id, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact
