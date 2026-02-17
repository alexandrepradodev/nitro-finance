from uuid import UUID
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import joinedload

from app.models.expense import Expense, ExpenseStatus, ExpenseType
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
    if month:
        try:
            year, month_num = month.split('-')
            year_int = int(year)
            month_int = int(month_num)
            # Primeiro dia do mês
            start_date = datetime(year_int, month_int, 1)
            # Último dia do mês
            if month_int == 12:
                end_date = datetime(year_int + 1, 1, 1)
            else:
                end_date = datetime(year_int, month_int + 1, 1)
            # Filtrar por created_at no mês
            filters.append(Expense.created_at >= start_date)
            filters.append(Expense.created_at < end_date)
        except (ValueError, IndexError):
            pass  # Ignora formato inválido
    
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
    
    # Total de todas as despesas ativas
    active_filters = base_filters + [Expense.status == ExpenseStatus.ACTIVE]
    total_value = db.query(func.sum(Expense.value_brl)).filter(and_(*active_filters)).scalar() or Decimal('0')
    
    # Total do mês (usar filtro se fornecido, senão mês atual)
    if month:
        try:
            year, month_num = month.split('-')
            year_int = int(year)
            month_int = int(month_num)
            first_day_month = datetime(year_int, month_int, 1)
            if month_int == 12:
                last_day_month = datetime(year_int + 1, 1, 1)
            else:
                last_day_month = datetime(year_int, month_int + 1, 1)
            monthly_filters = active_filters + [
                Expense.created_at >= first_day_month,
                Expense.created_at < last_day_month
            ]
        except (ValueError, IndexError):
            # Se formato inválido, usar mês atual
            now = datetime.now()
            first_day_month = datetime(now.year, now.month, 1)
            if now.month == 12:
                last_day_month = datetime(now.year + 1, 1, 1)
            else:
                last_day_month = datetime(now.year, now.month + 1, 1)
            monthly_filters = active_filters + [
                Expense.created_at >= first_day_month,
                Expense.created_at < last_day_month
            ]
    else:
        # Sem filtro de mês, usar mês atual
        now = datetime.now()
        first_day_month = datetime(now.year, now.month, 1)
        if now.month == 12:
            last_day_month = datetime(now.year + 1, 1, 1)
        else:
            last_day_month = datetime(now.year, now.month + 1, 1)
        monthly_filters = active_filters + [
            Expense.created_at >= first_day_month,
            Expense.created_at < last_day_month
        ]
    monthly_value = db.query(func.sum(Expense.value_brl)).filter(and_(*monthly_filters)).scalar() or Decimal('0')
    # Incluir despesas canceladas neste mês cujo valor conta no dashboard (já foi processada)
    month_date = first_day_month.date() if hasattr(first_day_month, 'date') else first_day_month
    cancelled_month_filters = base_filters + [
        Expense.status == ExpenseStatus.CANCELLED,
        Expense.cancellation_month == month_date,
        Expense.charged_when_cancelled == True,
    ]
    cancelled_month_value = db.query(func.sum(Expense.value_brl)).filter(and_(*cancelled_month_filters)).scalar() or Decimal('0')
    monthly_value = monthly_value + cancelled_month_value

    # Média por despesa
    active_count = db.query(func.count(Expense.id)).filter(and_(*active_filters)).scalar() or 0
    average_value = total_value / active_count if active_count > 0 else Decimal('0')
    
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
    base_filters = _get_base_filters(current_user, company_id, department_id, month)
    active_filters = base_filters + [Expense.status == ExpenseStatus.ACTIVE]
    
    results = db.query(
        Expense.category_id,
        Category.name.label('category_name'),
        func.sum(Expense.value_brl).label('total_value'),
        func.count(Expense.id).label('count')
    ).join(
        Category, Expense.category_id == Category.id
    ).filter(
        and_(*active_filters)
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
    base_filters = _get_base_filters(current_user, company_id, department_id, month)
    active_filters = base_filters + [Expense.status == ExpenseStatus.ACTIVE]
    
    results = db.query(
        Expense.company_id,
        Company.name.label('company_name'),
        func.sum(Expense.value_brl).label('total_value'),
        func.count(Expense.id).label('count')
    ).join(
        Company, Expense.company_id == Company.id
    ).filter(
        and_(*active_filters)
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
    base_filters = _get_base_filters(current_user, company_id, department_id, month)
    active_filters = base_filters + [Expense.status == ExpenseStatus.ACTIVE]
    
    results = db.query(
        Expense.department_id,
        Department.name.label('department_name'),
        Company.name.label('company_name'),
        func.sum(Expense.value_brl).label('total_value'),
        func.count(Expense.id).label('count')
    ).join(
        Department, Expense.department_id == Department.id
    ).join(
        Company, Expense.company_id == Company.id
    ).filter(
        and_(*active_filters)
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
    months: int = 6
) -> TimelineDataResponse:
    """Retorna dados de evolução de gastos ao longo do tempo"""
    base_filters = _get_base_filters(current_user, company_id, department_id)
    active_filters = base_filters + [Expense.status == ExpenseStatus.ACTIVE]
    
    # Calcular data inicial
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    results = db.query(
        func.date_trunc('month', Expense.created_at).label('month'),
        func.sum(Expense.value_brl).label('total_value'),
        func.count(Expense.id).label('count')
    ).filter(
        and_(*(active_filters + [Expense.created_at >= start_date]))
    ).group_by(
        func.date_trunc('month', Expense.created_at)
    ).order_by('month').all()
    
    data_points = []
    for result in results:
        if result.month:
            month_str = result.month.strftime('%Y-%m')
            data_points.append(TimelineDataPoint(
                month=month_str,
                total_value=result.total_value or Decimal('0'),
                count=result.count or 0
            ))
    
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
    base_filters = _get_base_filters(current_user, company_id, department_id, month)
    active_filters = base_filters + [Expense.status == ExpenseStatus.ACTIVE]
    
    expenses = db.query(Expense).options(
        joinedload(Expense.category),
        joinedload(Expense.company),
        joinedload(Expense.department),
    ).filter(
        and_(*active_filters)
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
