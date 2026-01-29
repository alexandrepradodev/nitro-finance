from sqlalchemy import Column, String, Boolean, Enum, ForeignKey, Numeric, Date, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.base import BaseModel


class ExpenseType(str, enum.Enum):
    RECURRING = "recurring"
    ONE_TIME = "one_time"


class Currency(str, enum.Enum):
    BRL = "BRL"
    USD = "USD"


class Periodicity(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"


class PaymentMethod(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BOLETO = "boleto"
    PIX = "pix"
    TRANSFER = "transfer"


class ExpenseStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    ACTIVE = "active"
    CANCELLATION_REQUESTED = "cancellation_requested"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    MIGRATED = "migrated"


class Expense(Base, BaseModel):
    __tablename__ = "expenses"

    # Identificação
    service_name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    expense_type = Column(Enum(ExpenseType), nullable=False)
    
    # Relacionamentos
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Valores
    value = Column(Numeric(12, 2), nullable=False)
    currency = Column(Enum(Currency), nullable=False)
    value_brl = Column(Numeric(12, 2), nullable=False)
    exchange_rate = Column(Numeric(10, 4), nullable=True)
    exchange_rate_date = Column(DateTime(timezone=True), nullable=True)
    
    # Recorrência
    periodicity = Column(Enum(Periodicity), nullable=True)
    renewal_date = Column(Date, nullable=True)
    
    # Pagamento
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    payment_identifier = Column(String(50), nullable=True)
    
    # Detalhes
    contracted_plan = Column(String(100), nullable=True)
    user_count = Column(Integer, nullable=True)
    evidence_link = Column(String(500), nullable=True)
    notes = Column(String(1000), nullable=True)
    
    # Status
    status = Column(Enum(ExpenseStatus), nullable=False, default=ExpenseStatus.DRAFT)
    
    # Relacionamentos ORM
    category = relationship("Category")
    company = relationship("Company")
    department = relationship("Department")
    owner = relationship("User", foreign_keys=[owner_id])
    approver = relationship("User", foreign_keys=[approver_id])