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
    code = Column(String(20), unique=True, nullable=False, index=True)
    service_name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    expense_type = Column(
        Enum(ExpenseType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    
    # Relacionamentos
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Valores
    value = Column(Numeric(12, 2), nullable=False)
    currency = Column(
        Enum(Currency, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    value_brl = Column(Numeric(12, 2), nullable=False)
    exchange_rate = Column(Numeric(10, 4), nullable=True)
    exchange_rate_date = Column(DateTime(timezone=True), nullable=True)
    
    # Recorrência
    periodicity = Column(
        Enum(Periodicity, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    renewal_date = Column(Date, nullable=True)
    
    # Pagamento
    payment_method = Column(
        Enum(PaymentMethod, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    payment_identifier = Column(String(50), nullable=True)
    
    # Detalhes
    contracted_plan = Column(String(100), nullable=True)
    user_count = Column(Integer, nullable=True)
    evidence_link = Column(String(500), nullable=True)
    login = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    notes = Column(String(1000), nullable=True)
    
    # Status
    status = Column(
        Enum(ExpenseStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ExpenseStatus.DRAFT,
    )
    cancellation_month = Column(Date, nullable=True)  # Primeiro dia do mês em que foi cancelada
    charged_when_cancelled = Column(Boolean, nullable=True)  # True = valor do mês conta no dashboard
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relacionamentos ORM
    category = relationship("Category")
    company = relationship("Company")
    department = relationship("Department")
    owner = relationship("User", foreign_keys=[owner_id])
    approver = relationship("User", foreign_keys=[approver_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    validations = relationship("ExpenseValidation", back_populates="expense")