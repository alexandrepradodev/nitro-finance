from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import BaseModel

class Company(Base, BaseModel):
    __tablename__="companies"

    name = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    departments = relationship("Department", back_populates="company")
    