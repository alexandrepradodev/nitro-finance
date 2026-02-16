from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.expense import ExpenseType, Currency, Periodicity, PaymentMethod, ExpenseStatus
from app.models.expense_validation import ValidationStatus


class ExpenseCreate(BaseModel):
    service_name: str
    description: str | None = None
    expense_type: ExpenseType
    category_id: UUID
    company_id: UUID
    department_id: UUID
    owner_id: UUID
    approver_id: UUID | None = None  # Se omitido, o endpoint usa owner_id (responsável = validador)
    value: Decimal
    currency: Currency
    periodicity: Periodicity | None = None
    renewal_date: date | None = None
    payment_method: PaymentMethod
    payment_identifier: str | None = None
    contracted_plan: str | None = None
    user_count: int | None = None
    evidence_link: str | None = None
    login: str | None = None
    password: str | None = None
    notes: str | None = None


class ExpenseCancelRequest(BaseModel):
    """Payload para cancelar despesa com informação se já foi processada no mês"""
    charged_this_month: bool
    cancellation_month: date | None = None  # Se não enviado, usa primeiro dia do mês atual


class ExpenseUpdate(BaseModel):
    service_name: str | None = None
    description: str | None = None
    expense_type: ExpenseType | None = None
    category_id: UUID | None = None
    company_id: UUID | None = None
    department_id: UUID | None = None
    owner_id: UUID | None = None
    approver_id: UUID | None = None
    value: Decimal | None = None
    currency: Currency | None = None
    periodicity: Periodicity | None = None
    renewal_date: date | None = None
    payment_method: PaymentMethod | None = None
    payment_identifier: str | None = None
    contracted_plan: str | None = None
    user_count: int | None = None
    evidence_link: str | None = None
    login: str | None = None
    password: str | None = None
    notes: str | None = None
    status: ExpenseStatus | None = None


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    service_name: str
    description: str | None
    expense_type: ExpenseType
    category_id: UUID
    company_id: UUID
    department_id: UUID
    owner_id: UUID
    approver_id: UUID
    value: Decimal
    currency: Currency
    value_brl: Decimal
    exchange_rate: Decimal | None
    exchange_rate_date: datetime | None
    periodicity: Periodicity | None
    renewal_date: date | None
    payment_method: PaymentMethod
    payment_identifier: str | None
    contracted_plan: str | None
    user_count: int | None
    evidence_link: str | None
    login: str | None
    password: str | None
    notes: str | None
    status: ExpenseStatus
    cancellation_month: date | None = None
    charged_when_cancelled: bool | None = None
    created_by_id: UUID | None = None
    cancelled_at: datetime | None = None
    cancelled_by_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class ExpenseValidationLogItem(BaseModel):
    """Item de log para histórico de validações da despesa."""
    validation_month: date
    status: ValidationStatus
    validated_at: datetime | None = None
    validator: "UserBasic | None" = None

    model_config = ConfigDict(from_attributes=True)


class ExpenseWithRelationsResponse(ExpenseResponse):
    category: "CategoryBasic"
    company: "CompanyBasic"
    department: "DepartmentBasic"
    owner: "UserBasic"
    approver: "UserBasic"
    created_by: "UserBasic | None" = None
    cancelled_at: datetime | None = None
    cancelled_by: "UserBasic | None" = None
    validations: list[ExpenseValidationLogItem] = []

    model_config = ConfigDict(from_attributes=True)


class CategoryBasic(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class CompanyBasic(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class DepartmentBasic(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class UserBasic(BaseModel):
    id: UUID
    name: str
    email: str

    class Config:
        from_attributes = True