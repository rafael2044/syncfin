from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import date
from app.database import Base


class Boleto(Base):
    __tablename__ = "boletos"

    id = Column(Integer, primary_key=True, index=True)
    numero_nota = Column(String(50), nullable=False)
    descricao = Column(String(200))
    valor = Column(Float, nullable=False)
    data_emissao = Column(Date, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    data_pagamento = Column(Date, nullable=True)
    pago = Column(Boolean, default=False)
    status = Column(String(20), default="pendente")
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    nota_fiscal_id = Column(Integer, ForeignKey("notas_fiscais.id"), nullable=True)
    anexo = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    payments = relationship("BoletoPayment", backref="boleto", cascade="all, delete-orphan")
    company = relationship("Company", back_populates="boletos")
    nota_fiscal = relationship("NotaFiscal", back_populates="boletos")

    def calcular_status(self):
        if self.pago:
            return "pago"
        if self.data_vencimento and self.data_vencimento < date.today():
            return "atrasado"
        return "pendente"


class BoletoPayment(Base):
    __tablename__ = "boleto_payments"

    id = Column(Integer, primary_key=True, index=True)
    boleto_id = Column(Integer, ForeignKey("boletos.id"), nullable=False)
    valor_pago = Column(Float, nullable=False)
    data_pagamento = Column(Date, nullable=False)
    observacao = Column(String(200))
    comprovante = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
