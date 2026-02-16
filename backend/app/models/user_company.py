from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base

user_companies = Table(
    "user_companies",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("company_id", UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True),
    UniqueConstraint("user_id", "company_id", name="uq_user_companies_user_company"),
)
