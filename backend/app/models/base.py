import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow(), onupdate=datetime.utcnow())

class BaseModel(TimestampMixin):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
