from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.base import BaseModel
from app.models.user_department import user_departments
from app.models.user_company import user_companies


class UserRole(str, enum.Enum):
    FINANCE_ADMIN = "finance_admin"
    SYSTEM_ADMIN = "system_admin"
    LEADER = "leader"


class User(Base, BaseModel):
    __tablename__ = "users"
    
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.LEADER)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relacionamentos
    departments = relationship(
        "Department",
        secondary=user_departments,
        back_populates="users",
    )
    companies = relationship(
        "Company",
        secondary=user_companies,
        back_populates="scoped_users",
    )