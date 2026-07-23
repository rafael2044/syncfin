from pydantic import BaseModel, EmailStr
from typing import Optional


class CompanyBase(BaseModel):
    name: str
    cnpj: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    cnpj: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class CompanyResponse(CompanyBase):
    id: int

    class Config:
        from_attributes = True
