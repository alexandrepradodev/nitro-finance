from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base

class UserDepartment(Base):
    __tablename__ = "user_departments"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), primary_key=True)