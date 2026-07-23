from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    cnpj = Column(String(18), unique=True, nullable=False)
    address = Column(String(200))
    phone = Column(String(20))
    email = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    notas_fiscais_recebidas = relationship("NotaFiscal", back_populates="empresa")
    boletos = relationship("Boleto", back_populates="company")
