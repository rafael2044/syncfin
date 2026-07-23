from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    reset_token = Column(String(200), nullable=True, unique=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)

    role = relationship("Role", backref="users")
