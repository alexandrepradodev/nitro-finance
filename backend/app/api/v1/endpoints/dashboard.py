from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import _role_value as role_value, get_expense_scope_params
from app.models.user import User, UserRole
from app.models.alert import Alert, AlertStatus
from app.models.expense_validation import ExpenseValidation, ValidationStatus
from app.models.expense import Expense
from app.services import dashboard_service
from app.schemas.dashboard import (
    DashboardStatsResponse,
    CategoryExpenseResponse,
    CompanyExpenseResponse,
    DepartmentExpenseResponse,
    TimelineDataResponse,
    TopExpenseResponse,
    StatusDistributionResponse,
    UpcomingRenewalsResponse,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def validate_dashboard_filters(
    current_user: User,
    company_id: UUID | None = None,
    department_id: UUID | None = None
):
    """Valida que os filtros de company_id e department_id estão no escopo do usuário"""
    role_val = role_value(current_user.role)
    
    # System Admin e Finance Admin têm acesso a tudo, não precisam validação
    if role_val in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
        return
    
    if role_val == UserRole.LEADER.value:
        # Para líder, validar que company_id está no escopo
        # department_id não precisa validação pois líder vê todos os departamentos das suas empresas
        if company_id:
            company_ids = [c.id for c in current_user.companies] if current_user.companies else []
            if company_id not in company_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não tem acesso a esta empresa"
                )


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    company_id: UUID | None = Query(None, description="Filtrar por empresa"),
    department_id: UUID | None = Query(None, description="Filtrar por setor"),
    month: str | None = Query(None, description="Filtrar por mês (formato YYYY-MM)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna estatísticas gerais do dashboard"""
    validate_dashboard_filters(current_user, company_id, department_id)
    stats = dashboard_service.get_dashboard_stats(db, current_user, company_id, department_id, month)
    
    # Calcular validações pendentes (respeitando filtro de empresa)
    user_role = role_value(current_user.role)
    if user_role in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
        validation_filters = [ExpenseValidation.status == ValidationStatus.PENDING]
        if company_id:
            validation_filters.append(Expense.company_id == company_id)
        if department_id:
            validation_filters.append(Expense.department_id == department_id)
        pending_validations = db.query(func.count(ExpenseValidation.id)).join(
            Expense, ExpenseValidation.expense_id == Expense.id
        ).filter(and_(*validation_filters)).scalar() or 0
    elif user_role == UserRole.LEADER.value:
        company_ids = [c.id for c in current_user.companies] if current_user.companies else []
        if company_ids:
            validation_filters = [
                ExpenseValidation.status == ValidationStatus.PENDING,
                Expense.owner_id == current_user.id,
                Expense.company_id.in_(company_ids),
            ]
            if company_id:
                validation_filters.append(Expense.company_id == company_id)
            if department_id:
                validation_filters.append(Expense.department_id == department_id)
            pending_validations = db.query(func.count(ExpenseValidation.id)).join(
                Expense, ExpenseValidation.expense_id == Expense.id
            ).filter(and_(*validation_filters)).scalar() or 0
        else:
            pending_validations = 0
    else:
        pending_validations = 0
    
    # Calcular alertas não lidos (respeitando filtro de empresa)
    if company_id:
        unread_alerts = db.query(func.count(Alert.id)).outerjoin(
            Expense, Alert.expense_id == Expense.id
        ).filter(
            and_(
                Alert.recipient_id == current_user.id,
                Alert.status == AlertStatus.PENDING,
                Expense.company_id == company_id,
            )
        ).scalar() or 0
    else:
        unread_alerts = db.query(func.count(Alert.id)).filter(
            and_(
                Alert.recipient_id == current_user.id,
                Alert.status == AlertStatus.PENDING,
            )
        ).scalar() or 0
    
    # Atualizar stats com valores calculados
    stats.pending_validations = pending_validations
    stats.unread_alerts = unread_alerts
    
    return stats


@router.get("/expenses-by-category", response_model=CategoryExpenseResponse)
def get_expenses_by_category(
    company_id: UUID | None = Query(None, description="Filtrar por empresa"),
    department_id: UUID | None = Query(None, description="Filtrar por setor"),
    month: str | None = Query(None, description="Filtrar por mês (formato YYYY-MM)"),
    limit: int = Query(10, le=50, description="Limite de resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna agregação de despesas por categoria"""
    validate_dashboard_filters(current_user, company_id, department_id)
    return dashboard_service.get_expenses_by_category(
        db, current_user, company_id, department_id, limit, month
    )


@router.get("/expenses-by-company", response_model=CompanyExpenseResponse)
def get_expenses_by_company(
    company_id: UUID | None = Query(None, description="Filtrar por empresa"),
    department_id: UUID | None = Query(None, description="Filtrar por setor"),
    month: str | None = Query(None, description="Filtrar por mês (formato YYYY-MM)"),
    limit: int = Query(10, le=50, description="Limite de resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna agregação de despesas por empresa"""
    validate_dashboard_filters(current_user, company_id, department_id)
    return dashboard_service.get_expenses_by_company(
        db, current_user, company_id, department_id, limit, month
    )


@router.get("/expenses-by-department", response_model=DepartmentExpenseResponse)
def get_expenses_by_department(
    company_id: UUID | None = Query(None, description="Filtrar por empresa"),
    department_id: UUID | None = Query(None, description="Filtrar por setor"),
    month: str | None = Query(None, description="Filtrar por mês (formato YYYY-MM)"),
    limit: int = Query(10, le=50, description="Limite de resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna agregação de despesas por setor"""
    validate_dashboard_filters(current_user, company_id, department_id)
    return dashboard_service.get_expenses_by_department(
        db, current_user, company_id, department_id, limit, month
    )


@router.get("/expenses-timeline", response_model=TimelineDataResponse)
def get_expenses_timeline(
    company_id: UUID | None = Query(None, description="Filtrar por empresa"),
    department_id: UUID | None = Query(None, description="Filtrar por setor"),
    months: int = Query(6, ge=1, le=12, description="Número de meses"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna dados de evolução de gastos ao longo do tempo"""
    validate_dashboard_filters(current_user, company_id, department_id)
    return dashboard_service.get_expenses_timeline(
        db, current_user, company_id, department_id, months
    )


@router.get("/top-expenses", response_model=TopExpenseResponse)
def get_top_expenses(
    company_id: UUID | None = Query(None, description="Filtrar por empresa"),
    department_id: UUID | None = Query(None, description="Filtrar por setor"),
    month: str | None = Query(None, description="Filtrar por mês (formato YYYY-MM)"),
    limit: int = Query(10, ge=1, le=50, description="Limite de resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna as maiores despesas"""
    validate_dashboard_filters(current_user, company_id, department_id)
    return dashboard_service.get_top_expenses(
        db, current_user, company_id, department_id, limit, month
    )


@router.get("/expenses-by-status", response_model=StatusDistributionResponse)
def get_expenses_by_status(
    company_id: UUID | None = Query(None, description="Filtrar por empresa"),
    department_id: UUID | None = Query(None, description="Filtrar por setor"),
    month: str | None = Query(None, description="Filtrar por mês (formato YYYY-MM)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna distribuição de despesas por status"""
    validate_dashboard_filters(current_user, company_id, department_id)
    return dashboard_service.get_expenses_by_status(
        db, current_user, company_id, department_id, month
    )


@router.get("/upcoming-renewals", response_model=UpcomingRenewalsResponse)
def get_upcoming_renewals(
    company_id: UUID | None = Query(None, description="Filtrar por empresa"),
    department_id: UUID | None = Query(None, description="Filtrar por setor"),
    days: int = Query(30, ge=1, le=90, description="Dias à frente para buscar"),
    limit: int = Query(10, ge=1, le=50, description="Limite de resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna próximas renovações"""
    validate_dashboard_filters(current_user, company_id, department_id)
    return dashboard_service.get_upcoming_renewals(
        db, current_user, company_id, department_id, days, limit
    )
