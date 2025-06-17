from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, condecimal, constr, ConfigDict


class ContactBase(BaseModel):
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    email: EmailStr = Field(..., max_length=100)
    phone: str = Field(..., max_length=50)
    birth_date: date
    additional_data: Optional[str] = None

    class Config:
        from_attributes = True


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    birth_date: Optional[date] = None
    additional_data: Optional[str] = None

    class Config:
        from_attributes = True


class ContactResponse(ContactBase):
    id: int
    user_id: int


class User(BaseModel):
    id: int
    username: str
    email: EmailStr = Field(..., max_length=100)
    avatar: Optional[str] = None
    confirmed: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str
    email: EmailStr = Field(..., max_length=100)
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class RequestEmail(BaseModel):
    email: EmailStr
