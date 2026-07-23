from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(20), nullable=False)
    entity = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    description = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="audit_logs")
