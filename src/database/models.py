from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Date, ForeignKey, DateTime, Boolean, func, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class UserRole(enum.Enum):
    """Enumeration for user roles in the system.

    This enum defines the available user roles that can be assigned
    to users for authorization and permission management.
    """

    USER = "user"
    ADMIN = "admin"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    This class serves as the declarative base for all database models
    in the application, providing common functionality and configuration.
    """

    pass


class User(Base):
    """User model representing registered users in the system.

    This model stores user account information including authentication
    credentials, profile data, and relationships to other entities.

    Attributes:
        id: Primary key identifier for the user.
        username: Unique username for the user account.
        email: Unique email address for the user.
        hashed_password: Securely hashed password for authentication.
        created_at: Timestamp when the user account was created.
        avatar: Optional URL or path to user's avatar image.
        confirmed: Boolean flag indicating if the user's email is confirmed.
        role: User's role in the system (USER or ADMIN).
        contacts: Relationship to the user's contact entries.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    avatar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)

    contacts = relationship(
        "Contact", back_populates="user", cascade="all, delete-orphan"
    )


class Contact(Base):
    """Contact model representing contact entries in the address book.

    This model stores contact information for individuals, including
    personal details and relationship to the user who owns the contact.

    Attributes:
        id: Primary key identifier for the contact.
        first_name: Contact's first name.
        last_name: Contact's last name.
        email: Contact's email address.
        phone: Contact's phone number.
        birth_date: Contact's date of birth.
        additional_data: Optional field for additional contact information.
        user_id: Foreign key linking to the user who owns this contact.
        user: Relationship to the User model who owns this contact.
    """

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(50), index=True)
    last_name: Mapped[str] = mapped_column(String(50), index=True)
    email: Mapped[str] = mapped_column(String(100), index=True)
    phone: Mapped[str] = mapped_column(String(50))
    birth_date: Mapped[date] = mapped_column(Date)
    additional_data: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="contacts")
