from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.base import BaseModel

class UserRole(str, enum.Enum):
    FINANCE_ADMIN = "finance_admin"
    SYSTEM_ADMIN = "system_admin"
    LEADER = "leader"
    USER = "user"

class User(Base, BaseModel):
    __tablename__ = "users"
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    phone = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    departments = relationship("Department", secondary="user_departments", back_populates="users")

