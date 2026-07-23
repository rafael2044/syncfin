from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role_id: Optional[int] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str
