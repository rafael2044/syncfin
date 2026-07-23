from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    phone = Column(String(20))
    email = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cnpjs = relationship("FornecedorCNPJ", backref="fornecedor", cascade="all, delete-orphan")
    notas_fiscais = relationship("NotaFiscal", back_populates="fornecedor")


class FornecedorCNPJ(Base):
    __tablename__ = "fornecedor_cnpjs"

    id = Column(Integer, primary_key=True, index=True)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id", ondelete="CASCADE"), nullable=False)
    cnpj = Column(String(20), nullable=False, unique=True)
