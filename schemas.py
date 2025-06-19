from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, condecimal, constr, ConfigDict
from enum import Enum


class UserRole(str, Enum):
    """Enumeration for user roles in API requests and responses.

    This enum defines the available user roles for validation and
    serialization in API operations.
    """

    USER = "user"
    ADMIN = "admin"


class ContactBase(BaseModel):
    """Base schema for contact data validation.

    This schema defines the common fields and validation rules for contact
    information used across create, update, and response operations.

    Attributes:
        first_name: Contact's first name (max 50 characters).
        last_name: Contact's last name (max 50 characters).
        email: Contact's email address (validated email format).
        phone: Contact's phone number (max 50 characters).
        birth_date: Contact's date of birth.
        additional_data: Optional additional information about the contact.
    """

    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    email: EmailStr = Field(..., max_length=100)
    phone: str = Field(..., max_length=50)
    birth_date: date
    additional_data: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContactCreate(ContactBase):
    """Schema for creating a new contact.

    Inherits all fields from ContactBase and is used for validating
    contact data when creating new contact entries.
    """

    pass


class ContactUpdate(BaseModel):
    """Schema for updating an existing contact.

    All fields are optional to allow partial updates of contact information.

    Attributes:
        first_name: Optional updated first name (max 50 characters).
        last_name: Optional updated last name (max 50 characters).
        email: Optional updated email address (validated email format).
        phone: Optional updated phone number (max 50 characters).
        birth_date: Optional updated date of birth.
        additional_data: Optional updated additional information.
    """

    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    birth_date: Optional[date] = None
    additional_data: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContactResponse(ContactBase):
    """Schema for contact API responses.

    Extends ContactBase with additional fields that are included
    in API responses but not in create/update requests.

    Attributes:
        id: Unique identifier for the contact.
        user_id: ID of the user who owns this contact.
    """

    id: int
    user_id: int


class User(BaseModel):
    """Schema for user data in API responses.

    Represents user information returned by the API, excluding
    sensitive data like passwords.

    Attributes:
        id: Unique identifier for the user.
        username: User's username.
        email: User's email address (validated email format).
        avatar: Optional URL to user's avatar image.
        confirmed: Boolean indicating if the user's email is confirmed.
        role: User's role in the system (USER or ADMIN).
    """

    id: int
    username: str
    email: EmailStr = Field(..., max_length=100)
    avatar: Optional[str] = None
    confirmed: bool = False
    role: UserRole = UserRole.USER

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Schema for user registration requests.

    Defines the required fields for creating a new user account.

    Attributes:
        username: Desired username for the account.
        email: User's email address (validated email format).
        password: User's password (will be hashed before storage).
    """

    username: str
    email: EmailStr = Field(..., max_length=100)
    password: str


class Token(BaseModel):
    """Schema for authentication token responses.

    Represents the structure of JWT tokens returned after successful
    authentication.

    Attributes:
        access_token: The JWT access token string.
        token_type: Type of token (typically "bearer").
    """

    access_token: str
    token_type: str


class RequestEmail(BaseModel):
    """Schema for email confirmation requests.

    Used for requesting email confirmation or resending confirmation emails.

    Attributes:
        email: Email address to send confirmation to.
    """

    email: EmailStr


class RequestPasswordReset(BaseModel):
    """Schema for password reset requests.

    Used when a user requests a password reset link.

    Attributes:
        email: Email address to send password reset link to.
    """

    email: EmailStr


class ConfirmPasswordReset(BaseModel):
    """Schema for confirming password reset.

    Used when a user confirms a password reset with a valid token.

    Attributes:
        email: Email address of the user resetting password.
        new_password: The new password to set.
        token: Password reset token for verification.
    """

    email: EmailStr
    new_password: str
    token: str
