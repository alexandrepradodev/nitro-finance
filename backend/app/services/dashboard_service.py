from uuid import UUID
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import joinedload

from app.models.expense import Expense, ExpenseStatus, ExpenseType
from app.models.expense_validation import ExpenseValidation, ValidationStatus
from app.models.category import Category
from app.models.company import Company
from app.models.department import Department
from app.models.user import User, UserRole
from app.schemas.dashboard import (
    DashboardStatsResponse,
    CategoryExpenseItem,
    CategoryExpenseResponse,
    CompanyExpenseItem,
    CompanyExpenseResponse,
    DepartmentExpenseItem,
    DepartmentExpenseResponse,
    TimelineDataPoint,
    TimelineDataResponse,
    TopExpenseItem,
    TopExpenseResponse,
    StatusDistributionItem,
    StatusDistributionResponse,
    UpcomingRenewalItem,
    UpcomingRenewalsResponse,
)


KNOWN_ROLES = frozenset({
    UserRole.SYSTEM_ADMIN.value,
    UserRole.FINANCE_ADMIN.value,
    UserRole.LEADER.value,
})


def _role_value(role) -> str:
    """Normaliza role para string (enum ou string do DB)."""
    return role.value if hasattr(role, "value") else str(role)


def _get_base_filters(
    current_user: User,
    company_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    month: Optional[str] = None
):
    """Retorna lista de filtros base para despesas (escopo por empresa + responsável/created_by)."""
    filters = []
    role_val = (_role_value(current_user.role) or "").strip()
    if not role_val or role_val not in KNOWN_ROLES:
        # Fallback seguro: restringir ao criador (sem acesso amplo)
        filters.append(Expense.created_by_id == current_user.id)
        if company_id:
            filters.append(Expense.company_id == company_id)
        if department_id:
            filters.append(Expense.department_id == department_id)
        return filters

    if role_val in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
        if company_id:
            filters.append(Expense.company_id == company_id)
        if department_id:
            filters.append(Expense.department_id == department_id)
    elif role_val == UserRole.LEADER.value:
        company_ids = [c.id for c in current_user.companies] if current_user.companies else []
        if not company_ids:
            filters.append(Expense.company_id.in_([]))
        else:
            filters.append(Expense.company_id.in_(company_ids))
            if company_id:
                filters.append(Expense.company_id == company_id)
            if department_id:
                filters.append(Expense.department_id == department_id)
    else:
        filters.append(Expense.created_by_id == current_user.id)
        if company_id:
            filters.append(Expense.company_id == company_id)
        if department_id:
            filters.append(Expense.department_id == department_id)

    # Filtro por mês (formato YYYY-MM)
    # Recorrentes: incluir em todos os meses. One-time: apenas criadas no mês.
    if month:
        try:
            year, month_num = month.split('-')
            year_int = int(year)
            month_int = int(month_num)
            start_date = datetime(year_int, month_int, 1)
            if month_int == 12:
                end_date = datetime(year_int + 1, 1, 1)
            else:
                end_date = datetime(year_int, month_int + 1, 1)
            filters.append(
                or_(
                    Expense.expense_type == ExpenseType.RECURRING,
                    and_(
                        Expense.created_at >= start_date,
                        Expense.created_at < end_date
                    )
                )
            )
        except (ValueError, IndexError):
            pass  # Ignora formato inválido

    return filters


def _parse_month_start(month: Optional[str]) -> Optional[date]:
    if not month:
        return None
    try:
        year, month_num = month.split('-')
        return date(int(year), int(month_num), 1)
    except (ValueError, IndexError):
        return None


def _get_approved_validation_filters(
    current_user: User,
    company_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    month: Optional[str] = None,
):
    filters = [
        *_get_base_filters(current_user, company_id, department_id, month=None),
        ExpenseValidation.status == ValidationStatus.APPROVED,
    ]
    month_start = _parse_month_start(month)
    if month_start:
        filters.append(ExpenseValidation.validation_month == month_start)
    return filters


def get_dashboard_stats(
    db: Session,
    current_user: User,
    company_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    month: Optional[str] = None
) -> DashboardStatsResponse:
    """Calcula estatísticas gerais do dashboard"""
    base_filters = _get_base_filters(current_user, company_id, department_id, month)
    scope_filters = _get_base_filters(current_user, company_id, department_id, month=None)

    # Mês atual (sempre) e ano alvo (do filtro ou atual)
    now = datetime.now()
    current_month_date = date(now.year, now.month, 1)
    month_start = _parse_month_start(month)
    target_year = month_start.year if month_start else current_month_date.year

    year_start = date(target_year, 1, 1)
    year_end = date(target_year, 12, 1)

    approved_year_filters = [
        *scope_filters,
        ExpenseValidation.status == ValidationStatus.APPROVED,
        ExpenseValidation.validation_month >= year_start,
        ExpenseValidation.validation_month <= year_end,
    ]

    # Total do Ano: soma de validações APROVADAS no ano do filtro (ou ano atual sem filtro)
    total_value = db.query(func.sum(Expense.value_brl)).join(
        ExpenseValidation, ExpenseValidation.expense_id == Expense.id
    ).filter(and_(*approved_year_filters)).scalar() or Decimal('0')

    # Total Mensal: soma de validações APROVADAS.
    # - com month selecionado: apenas o mês informado
    # - sem month: soma de todo o histórico aprovado
    approved_monthly_filters = _get_approved_validation_filters(
        current_user=current_user,
        company_id=company_id,
        department_id=department_id,
        month=month,
    )

    monthly_value = db.query(func.sum(Expense.value_brl)).join(
        ExpenseValidation, ExpenseValidation.expense_id == Expense.id
    ).filter(and_(*approved_monthly_filters)).scalar() or Decimal('0')

    # Média por despesa e demais contagens (respeitam filtro de mês)
    active_filters = base_filters + [Expense.status == ExpenseStatus.ACTIVE]

    active_count = db.query(func.count(Expense.id)).filter(and_(*active_filters)).scalar() or 0
    filtered_total_value = db.query(func.sum(Expense.value_brl)).filter(and_(*active_filters)).scalar() or Decimal('0')
    average_value = filtered_total_value / active_count if active_count > 0 else Decimal('0')
    
    # Despesas recorrentes vs únicas
    recurring_count = db.query(func.count(Expense.id)).filter(
        and_(*(active_filters + [Expense.expense_type == ExpenseType.RECURRING]))
    ).scalar() or 0
    one_time_count = db.query(func.count(Expense.id)).filter(
        and_(*(active_filters + [Expense.expense_type == ExpenseType.ONE_TIME]))
    ).scalar() or 0
    
    # Despesas canceladas (economia potencial)
    cancelled_filters = base_filters + [Expense.status == ExpenseStatus.CANCELLED]
    cancelled_value = db.query(func.sum(Expense.value_brl)).filter(and_(*cancelled_filters)).scalar() or Decimal('0')
    
    # Próximas renovações (próximos 30 dias)
    today = date.today()
    next_month = today + timedelta(days=30)
    upcoming_renewals = db.query(func.count(Expense.id)).filter(
        and_(*(
            active_filters + [
                Expense.renewal_date.isnot(None),
                Expense.renewal_date >= today,
                Expense.renewal_date <= next_month
            ]
        ))
    ).scalar() or 0
    
    return DashboardStatsResponse(
        total_expenses_value=total_value,
        monthly_expenses_value=monthly_value,
        average_expense_value=average_value,
        pending_validations=0,  # Será calculado no endpoint
        overdue_validations=0,  # Será calculado no endpoint
        unread_alerts=0,  # Será calculado no endpoint
        active_expenses=active_count,
        recurring_expenses=recurring_count,
        one_time_expenses=one_time_count,
        upcoming_renewals=upcoming_renewals,
        cancelled_expenses_value=cancelled_value,
    )


def get_expenses_by_category(
    db: Session,
    current_user: User,
    company_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    limit: int = 10,
    month: Optional[str] = None
) -> CategoryExpenseResponse:
    """Agrega despesas por categoria"""
    approved_filters = _get_approved_validation_filters(
        current_user=current_user,
        company_id=company_id,
        department_id=department_id,
        month=month,
    )
    
    results = db.query(
        Expense.category_id,
        Category.name.label('category_name'),
        func.sum(Expense.value_brl).label('total_value'),
        func.count(ExpenseValidation.id).label('count')
    ).join(
        ExpenseValidation, ExpenseValidation.expense_id == Expense.id
    ).join(
        Category, Expense.category_id == Category.id
    ).filter(
        and_(*approved_filters)
    ).group_by(
        Expense.category_id, Category.name
    ).order_by(
        func.sum(Expense.value_brl).desc()
    ).limit(limit).all()
    
    total = sum(r.total_value for r in results) or Decimal('0')
    
    items = []
    for result in results:
        percentage = float((result.total_value / total * 100)) if total > 0 else 0.0
        
        items.append(CategoryExpenseItem(
            category_id=result.category_id,
            category_name=result.category_name or 'N/A',
            total_value=result.total_value or Decimal('0'),
            count=result.count or 0,
            percentage=percentage
        ))
    
    return CategoryExpenseResponse(items=items, total=total)


def get_expenses_by_company(
    db: Session,
    current_user: User,
    company_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    limit: int = 10,
    month: Optional[str] = None
) -> CompanyExpenseResponse:
    """Agrega despesas por empresa"""
    approved_filters = _get_approved_validation_filters(
        current_user=current_user,
        company_id=company_id,
        department_id=department_id,
        month=month,
    )
    
    results = db.query(
        Expense.company_id,
        Company.name.label('company_name'),
        func.sum(Expense.value_brl).label('total_value'),
        func.count(ExpenseValidation.id).label('count')
    ).join(
        ExpenseValidation, ExpenseValidation.expense_id == Expense.id
    ).join(
        Company, Expense.company_id == Company.id
    ).filter(
        and_(*approved_filters)
    ).group_by(
        Expense.company_id, Company.name
    ).order_by(
        func.sum(Expense.value_brl).desc()
    ).limit(limit).all()
    
    total = sum(r.total_value for r in results) or Decimal('0')
    
    items = []
    for result in results:
        percentage = float((result.total_value / total * 100)) if total > 0 else 0.0
        
        items.append(CompanyExpenseItem(
            company_id=result.company_id,
            company_name=result.company_name or 'N/A',
            total_value=result.total_value or Decimal('0'),
            count=result.count or 0,
            percentage=percentage
        ))
    
    return CompanyExpenseResponse(items=items, total=total)


def get_expenses_by_department(
    db: Session,
    current_user: User,
    company_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    limit: int = 10,
    month: Optional[str] = None
) -> DepartmentExpenseResponse:
    """Agrega despesas por setor"""
    approved_filters = _get_approved_validation_filters(
        current_user=current_user,
        company_id=company_id,
        department_id=department_id,
        month=month,
    )
    
    results = db.query(
        Expense.department_id,
        Department.name.label('department_name'),
        Company.name.label('company_name'),
        func.sum(Expense.value_brl).label('total_value'),
        func.count(ExpenseValidation.id).label('count')
    ).join(
        ExpenseValidation, ExpenseValidation.expense_id == Expense.id
    ).join(
        Department, Expense.department_id == Department.id
    ).join(
        Company, Expense.company_id == Company.id
    ).filter(
        and_(*approved_filters)
    ).group_by(
        Expense.department_id, Department.name, Company.name
    ).order_by(
        func.sum(Expense.value_brl).desc()
    ).limit(limit).all()
    
    total = sum(r.total_value for r in results) or Decimal('0')
    
    items = []
    for result in results:
        percentage = float((result.total_value / total * 100)) if total > 0 else 0.0
        
        items.append(DepartmentExpenseItem(
            department_id=result.department_id,
            department_name=result.department_name or 'N/A',
            company_name=result.company_name or 'N/A',
            total_value=result.total_value or Decimal('0'),
            count=result.count or 0,
            percentage=percentage
        ))
    
    return DepartmentExpenseResponse(items=items, total=total)


def get_expenses_timeline(
    db: Session,
    current_user: User,
    company_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    months: int = 6,
    month: Optional[str] = None,
) -> TimelineDataResponse:
    """Retorna dados de evolução de gastos ao longo do tempo com validações aprovadas."""
    scope_filters = _get_base_filters(current_user, company_id, department_id, month=None)

    now = datetime.now()
    end_first = date(now.year, now.month, 1)
    if month:
        try:
            year, month_num = month.split('-')
            end_first = date(int(year), int(month_num), 1)
        except (ValueError, IndexError):
            pass

    start_date = end_first - timedelta(days=months * 30)
    start_first = start_date.replace(day=1)

    results = db.query(
        ExpenseValidation.validation_month,
        func.sum(Expense.value_brl).label('total'),
        func.count(Expense.id).label('count'),
    ).join(
        Expense, ExpenseValidation.expense_id == Expense.id
    ).filter(and_(
        *scope_filters,
        ExpenseValidation.validation_month >= start_first,
        ExpenseValidation.validation_month <= end_first,
        ExpenseValidation.status == ValidationStatus.APPROVED,
    )).group_by(
        ExpenseValidation.validation_month
    ).all()

    month_totals: dict[str, Decimal] = {}
    month_counts: dict[str, int] = {}
    current = start_first
    while current <= end_first:
        key = current.strftime('%Y-%m')
        month_totals[key] = Decimal('0')
        month_counts[key] = 0
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    for row in results:
        month_key = row.validation_month.strftime('%Y-%m')
        if month_key in month_totals:
            month_totals[month_key] = row.total or Decimal('0')
            month_counts[month_key] = row.count or 0

    data_points = [
        TimelineDataPoint(month=k, total_value=v, count=month_counts[k])
        for k, v in sorted(month_totals.items())
    ]
    return TimelineDataResponse(data=data_points)


def get_top_expenses(
    db: Session,
    current_user: User,
    company_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    limit: int = 10,
    month: Optional[str] = None
) -> TopExpenseResponse:
    """Retorna as maiores despesas"""
    approved_filters = _get_approved_validation_filters(
        current_user=current_user,
        company_id=company_id,
        department_id=department_id,
        month=month,
    )
    
    expenses = db.query(Expense).options(
        joinedload(Expense.category),
        joinedload(Expense.company),
        joinedload(Expense.department),
    ).join(
        ExpenseValidation, ExpenseValidation.expense_id == Expense.id
    ).filter(
        and_(*approved_filters)
    ).distinct(
        Expense.id
    ).order_by(
        Expense.value_brl.desc()
    ).limit(limit).all()
    
    items = []
    for expense in expenses:
        items.append(TopExpenseItem(
            expense_id=expense.id,
            service_name=expense.service_name,
            category_name=expense.category.name if expense.category else 'N/A',
            company_name=expense.company.name if expense.company else 'N/A',
            department_name=expense.department.name if expense.department else 'N/A',
            value=expense.value,
            currency=expense.currency,
            value_brl=expense.value_brl,
            status=expense.status
        ))
    
    return TopExpenseResponse(items=items)


def get_expenses_by_status(
    db: Session,
    current_user: User,
    company_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    month: Optional[str] = None
) -> StatusDistributionResponse:
    """Distribuição de despesas por status"""
    base_filters = _get_base_filters(current_user, company_id, department_id, month)
    
    results = db.query(
        Expense.status,
        func.count(Expense.id).label('count'),
        func.sum(Expense.value_brl).label('total_value')
    ).filter(
        and_(*base_filters)
    ).group_by(
        Expense.status
    ).all()
    
    total_count = sum(r.count for r in results) or 0
    total_value = sum(r.total_value for r in results) or Decimal('0')
    
    items = []
    for result in results:
        percentage = float((result.count / total_count * 100)) if total_count > 0 else 0.0
        
        items.append(StatusDistributionItem(
            status=result.status,
            count=result.count or 0,
            total_value=result.total_value or Decimal('0'),
            percentage=percentage
        ))
    
    return StatusDistributionResponse(
        items=items,
        total_count=total_count,
        total_value=total_value
    )


def get_upcoming_renewals(
    db: Session,
    current_user: User,
    company_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    days: int = 30,
    limit: int = 10
) -> UpcomingRenewalsResponse:
    """Retorna próximas renovações"""
    base_filters = _get_base_filters(current_user, company_id, department_id)
    
    today = date.today()
    end_date = today + timedelta(days=days)
    
    expenses = db.query(Expense).filter(
        and_(*(base_filters + [
            Expense.status == ExpenseStatus.ACTIVE,
            Expense.renewal_date.isnot(None),
            Expense.renewal_date >= today,
            Expense.renewal_date <= end_date
        ]))
    ).order_by(
        Expense.renewal_date.asc()
    ).limit(limit).all()
    
    items = []
    for expense in expenses:
        if expense.renewal_date:
            days_until = (expense.renewal_date - today).days
            
            items.append(UpcomingRenewalItem(
                expense_id=expense.id,
                service_name=expense.service_name,
                renewal_date=expense.renewal_date,
                value=expense.value,
                currency=expense.currency,
                value_brl=expense.value_brl,
                days_until_renewal=days_until
            ))
    
    return UpcomingRenewalsResponse(items=items, count=len(items))
