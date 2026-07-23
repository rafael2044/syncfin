from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class NotaFiscal(Base):
    __tablename__ = "notas_fiscais"

    id = Column(Integer, primary_key=True, index=True)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=False)
    fornecedor_cnpj = Column(String(20), nullable=False)
    empresa_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    empresa_cnpj = Column(String(20), nullable=False)
    tipo_material_id = Column(Integer, ForeignKey("tipos_material.id"), nullable=False)
    numero = Column(String(50), nullable=False)
    descricao = Column(String(200))
    data_emissao = Column(Date, nullable=False)
    valor_total = Column(Float, nullable=False)
    anexo = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    fornecedor = relationship("Fornecedor", back_populates="notas_fiscais")
    empresa = relationship("Company", back_populates="notas_fiscais_recebidas")
    tipo_material = relationship("TipoMaterial", back_populates="notas_fiscais")
    boletos = relationship("Boleto", back_populates="nota_fiscal", cascade="all, delete-orphan")
