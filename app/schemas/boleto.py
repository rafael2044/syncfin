from pydantic import BaseModel
from typing import Optional
from datetime import date


class BoletoBase(BaseModel):
    numero_nota: str
    descricao: Optional[str] = None
    category_id: int
    valor: float
    data_emissao: date
    data_vencimento: date
    company_id: int


class BoletoCreate(BoletoBase):
    pass


class BoletoUpdate(BaseModel):
    numero_nota: Optional[str] = None
    descricao: Optional[str] = None
    category_id: Optional[int] = None
    valor: Optional[float] = None
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    pago: Optional[bool] = None


class BoletoResponse(BoletoBase):
    id: int
    pago: bool
    data_pagamento: Optional[date] = None

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    valor_pago: float
    data_pagamento: date
    observacao: Optional[str] = None
