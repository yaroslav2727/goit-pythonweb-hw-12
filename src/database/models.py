from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Date, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    avatar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    contacts = relationship(
        "Contact", back_populates="user", cascade="all, delete-orphan"
    )


class Contact(Base):
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
