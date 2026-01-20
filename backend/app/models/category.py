from sqlalchemy import Column, String, Boolean
from app.core.database import Base
from app.models.base import BaseModel

class Category(Base, BaseModel):
    __tablename__ = "categories"

    name = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)