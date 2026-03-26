from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.models.expense import ExpenseStatus, ExpenseType, Currency


class DashboardStatsResponse(BaseModel):
    total_expenses_value: Decimal
    monthly_expenses_value: Decimal
    average_expense_value: Decimal
    pending_validations: int
    overdue_validations: int
    unread_alerts: int
    active_expenses: int
    recurring_expenses: int
    one_time_expenses: int
    upcoming_renewals: int
    cancelled_expenses_value: Decimal


class CategoryExpenseItem(BaseModel):
    category_id: UUID
    category_name: str
    total_value: Decimal
    count: int
    percentage: float


class CategoryExpenseResponse(BaseModel):
    items: list[CategoryExpenseItem]
    total: Decimal


class CompanyExpenseItem(BaseModel):
    company_id: UUID
    company_name: str
    total_value: Decimal
    count: int
    percentage: float


class CompanyExpenseResponse(BaseModel):
    items: list[CompanyExpenseItem]
    total: Decimal


class DepartmentExpenseItem(BaseModel):
    department_id: UUID
    department_name: str
    company_name: str
    total_value: Decimal
    count: int
    percentage: float


class DepartmentExpenseResponse(BaseModel):
    items: list[DepartmentExpenseItem]
    total: Decimal


class TimelineDataPoint(BaseModel):
    month: str  # YYYY-MM
    total_value: Decimal
    count: int


class TimelineDataResponse(BaseModel):
    data: list[TimelineDataPoint]


class TopExpenseItem(BaseModel):
    expense_id: UUID
    service_name: str
    category_name: str
    company_name: str
    department_name: str
    value: Decimal
    currency: Currency
    value_brl: Decimal
    status: ExpenseStatus


class TopExpenseResponse(BaseModel):
    items: list[TopExpenseItem]


class StatusDistributionItem(BaseModel):
    status: ExpenseStatus
    count: int
    total_value: Decimal
    percentage: float


class StatusDistributionResponse(BaseModel):
    items: list[StatusDistributionItem]
    total_count: int
    total_value: Decimal


class UpcomingRenewalItem(BaseModel):
    expense_id: UUID
    service_name: str
    renewal_date: date
    value: Decimal
    currency: Currency
    value_brl: Decimal
    days_until_renewal: int


class UpcomingRenewalsResponse(BaseModel):
    items: list[UpcomingRenewalItem]
    count: int
