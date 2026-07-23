from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class TipoMaterial(Base):
    __tablename__ = "tipos_material"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    notas_fiscais = relationship("NotaFiscal", back_populates="tipo_material")
