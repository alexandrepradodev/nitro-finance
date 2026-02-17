from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.models.expense_validation import ValidationStatus


class ExpenseValidationCreate(BaseModel):
    """Schema interno para criação automática de validações"""
    expense_id: UUID
    validator_id: UUID | None = None
    validation_month: date


class ExpenseValidationUpdate(BaseModel):
    """Schema para atualizar validação (aprovado/rejeitado)"""
    status: ValidationStatus


class RejectRequest(BaseModel):
    """Body opcional ao rejeitar: se a despesa já foi processada no mês (valor conta no dashboard)"""
    charged_this_month: bool = False


class ExpenseValidationResponse(BaseModel):
    """Schema básico de resposta de validação"""
    id: UUID | None = None  # Opcional para validações previstas
    expense_id: UUID
    validator_id: UUID | None
    validation_month: date
    status: ValidationStatus
    validated_at: datetime | None
    is_overdue: bool = False
    is_predicted: bool = False  # Indica se é uma validação prevista (não criada)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class CompanyBasic(BaseModel):
    """Schema básico de empresa"""
    id: UUID
    name: str

    class Config:
        from_attributes = True


class DepartmentBasic(BaseModel):
    """Schema básico de departamento"""
    id: UUID
    name: str

    class Config:
        from_attributes = True


class UserBasic(BaseModel):
    """Schema básico de usuário para incluir em validações"""
    id: UUID
    name: str
    email: str

    class Config:
        from_attributes = True


class ExpenseBasic(BaseModel):
    """Schema básico de despesa para incluir em validações"""
    id: UUID
    code: str
    service_name: str
    value: Decimal
    currency: str
    value_brl: Decimal
    status: str
    department_id: UUID
    company: Optional[CompanyBasic] = None
    department: Optional[DepartmentBasic] = None
    owner: Optional[UserBasic] = None

    class Config:
        from_attributes = True


class ExpenseValidationWithExpenseResponse(ExpenseValidationResponse):
    """Schema de resposta com dados da despesa e validador"""
    expense: ExpenseBasic
    validator: UserBasic | None = None

    class Config:
        from_attributes = True
