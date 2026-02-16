from uuid import UUID
from decimal import Decimal
from datetime import datetime, timezone, date

from sqlalchemy.orm import Session, joinedload

from app.models.expense import Expense, Currency, ExpenseStatus, ExpenseType
from app.models.expense_validation import ExpenseValidation
from app.schemas.expense import ExpenseCreate, ExpenseUpdate


def _next_expense_code(db: Session) -> str:
    """Retorna o próximo código sequencial (DP01, DP02, ...)."""
    codes = db.query(Expense.code).filter(Expense.code.isnot(None)).all()
    numbers = []
    for (code,) in codes:
        if code and code.startswith("DP"):
            suffix = code[2:].lstrip("0") or "0"
            if suffix.isdigit():
                numbers.append(int(suffix))
    next_num = max(numbers, default=0) + 1
    return f"DP{next_num:02d}" if next_num < 100 else f"DP{next_num}"


def get_all(db: Session) -> list[Expense]:
    """Lista todas as despesas com relacionamentos"""
    return db.query(Expense)\
        .options(
            joinedload(Expense.category),
            joinedload(Expense.company),
            joinedload(Expense.department),
            joinedload(Expense.owner),
            joinedload(Expense.approver)
        )\
        .all()


def get_filtered(
    db: Session,
    company_ids: list[UUID] | None = None,
    department_ids: list[UUID] | None = None,
    owner_ids: list[UUID] | None = None,
    created_by_id: UUID | None = None,
    category_ids: list[UUID] | None = None,
    statuses: list[ExpenseStatus] | None = None,
    expense_types: list[ExpenseType] | None = None,
) -> list[Expense]:
    """Lista despesas com filtros opcionais (listas). Lista vazia = nenhum resultado, None = não filtra."""
    query = db.query(Expense).options(
        joinedload(Expense.category),
        joinedload(Expense.company),
        joinedload(Expense.department),
        joinedload(Expense.owner),
        joinedload(Expense.approver),
    )
    
    # Tratar company_ids: lista vazia = nenhum resultado
    if company_ids is not None:
        if len(company_ids) == 0:
            return []
        query = query.filter(Expense.company_id.in_(company_ids))
    
    # Tratar department_ids: lista vazia = nenhum resultado
    if department_ids is not None:
        if len(department_ids) == 0:
            return []
        query = query.filter(Expense.department_id.in_(department_ids))
    
    # Tratar owner_ids: lista vazia = nenhum resultado
    if owner_ids is not None:
        if len(owner_ids) == 0:
            return []
        query = query.filter(Expense.owner_id.in_(owner_ids))
    
    if created_by_id is not None:
        query = query.filter(Expense.created_by_id == created_by_id)
    if category_ids:
        query = query.filter(Expense.category_id.in_(category_ids))
    if statuses:
        query = query.filter(Expense.status.in_(statuses))
    if expense_types:
        query = query.filter(Expense.expense_type.in_(expense_types))
    query = query.order_by(Expense.created_at.desc())
    return query.all()


def get_by_id(db: Session, expense_id: UUID) -> Expense | None:
    """Busca despesa por ID com relacionamentos (inclui validations e validator para histórico)."""
    return db.query(Expense)\
        .options(
            joinedload(Expense.category),
            joinedload(Expense.company),
            joinedload(Expense.department),
            joinedload(Expense.owner),
            joinedload(Expense.approver),
            joinedload(Expense.created_by),
            joinedload(Expense.cancelled_by),
            joinedload(Expense.validations).joinedload(ExpenseValidation.validator),
        )\
        .filter(Expense.id == expense_id)\
        .first()


def get_by_department(db: Session, department_id: UUID) -> list[Expense]:
    """Lista despesas de um departamento com relacionamentos"""
    return db.query(Expense)\
        .options(
            joinedload(Expense.category),
            joinedload(Expense.company),
            joinedload(Expense.department),
            joinedload(Expense.owner),
            joinedload(Expense.approver)
        )\
        .filter(Expense.department_id == department_id)\
        .all()


def get_by_company(db: Session, company_id: UUID) -> list[Expense]:
    """Lista despesas de uma empresa com relacionamentos"""
    return db.query(Expense)\
        .options(
            joinedload(Expense.category),
            joinedload(Expense.company),
            joinedload(Expense.department),
            joinedload(Expense.owner),
            joinedload(Expense.approver)
        )\
        .filter(Expense.company_id == company_id)\
        .all()


def get_by_owner(db: Session, owner_id: UUID) -> list[Expense]:
    """Lista despesas de um responsável com relacionamentos"""
    return db.query(Expense)\
        .options(
            joinedload(Expense.category),
            joinedload(Expense.company),
            joinedload(Expense.department),
            joinedload(Expense.owner),
            joinedload(Expense.approver)
        )\
        .filter(Expense.owner_id == owner_id)\
        .all()


def get_by_status(db: Session, status: ExpenseStatus) -> list[Expense]:
    """Lista despesas por status com relacionamentos"""
    return db.query(Expense)\
        .options(
            joinedload(Expense.category),
            joinedload(Expense.company),
            joinedload(Expense.department),
            joinedload(Expense.owner),
            joinedload(Expense.approver)
        )\
        .filter(Expense.status == status)\
        .all()


def create(
    db: Session,
    data: ExpenseCreate,
    value_brl: Decimal,
    exchange_rate: Decimal | None = None,
    exchange_rate_date: datetime | None = None,
    created_by_id: UUID | None = None,
) -> Expense:
    """Cria nova despesa"""
    code = _next_expense_code(db)
    expense = Expense(
        code=code,
        service_name=data.service_name,
        description=data.description,
        expense_type=data.expense_type,
        category_id=data.category_id,
        company_id=data.company_id,
        department_id=data.department_id,
        owner_id=data.owner_id,
        approver_id=data.approver_id,
        value=data.value,
        currency=data.currency,
        value_brl=value_brl,
        exchange_rate=exchange_rate,
        exchange_rate_date=exchange_rate_date,
        periodicity=data.periodicity,
        renewal_date=data.renewal_date,
        payment_method=data.payment_method,
        payment_identifier=data.payment_identifier,
        contracted_plan=data.contracted_plan,
        user_count=data.user_count,
        evidence_link=data.evidence_link,
        login=data.login,
        password=data.password,
        notes=data.notes,
        status=ExpenseStatus.ACTIVE,
        created_by_id=created_by_id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def update(
    db: Session,
    expense: Expense,
    data: ExpenseUpdate,
    value_brl: Decimal | None = None,
    exchange_rate: Decimal | None = None,
    exchange_rate_date: datetime | None = None
) -> Expense:
    """Atualiza despesa existente"""
    if data.service_name is not None:
        expense.service_name = data.service_name
    if data.description is not None:
        expense.description = data.description
    if data.expense_type is not None:
        expense.expense_type = data.expense_type
    if data.category_id is not None:
        expense.category_id = data.category_id
    if data.company_id is not None:
        expense.company_id = data.company_id
    if data.department_id is not None:
        expense.department_id = data.department_id
    if data.owner_id is not None:
        expense.owner_id = data.owner_id
    if data.approver_id is not None:
        expense.approver_id = data.approver_id
    if data.value is not None:
        expense.value = data.value
    if data.currency is not None:
        expense.currency = data.currency
    if value_brl is not None:
        expense.value_brl = value_brl
    if exchange_rate is not None:
        expense.exchange_rate = exchange_rate
    if exchange_rate_date is not None:
        expense.exchange_rate_date = exchange_rate_date
    if data.periodicity is not None:
        expense.periodicity = data.periodicity
    if data.renewal_date is not None:
        expense.renewal_date = data.renewal_date
    if data.payment_method is not None:
        expense.payment_method = data.payment_method
    if data.payment_identifier is not None:
        expense.payment_identifier = data.payment_identifier
    if data.contracted_plan is not None:
        expense.contracted_plan = data.contracted_plan
    if data.user_count is not None:
        expense.user_count = data.user_count
    if data.evidence_link is not None:
        expense.evidence_link = data.evidence_link
    if data.login is not None:
        expense.login = data.login
    if data.password is not None:
        expense.password = data.password
    if data.notes is not None:
        expense.notes = data.notes
    if data.status is not None:
        expense.status = data.status

    expense.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(expense)
    return expense


def delete(db: Session, expense: Expense) -> Expense:
    """Cancela despesa (soft delete)"""
    expense.status = ExpenseStatus.CANCELLED
    expense.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(expense)
    return expense


def cancel_with_info(
    db: Session,
    expense: Expense,
    charged_this_month: bool,
    cancellation_month: date | None = None,
    cancelled_by_id: UUID | None = None,
) -> Expense:
    """Cancela despesa registrando mês e se o valor do mês deve contar no dashboard."""
    now = datetime.now(timezone.utc)
    if cancellation_month is None:
        cancellation_month = now.date().replace(day=1)
    expense.status = ExpenseStatus.CANCELLED
    expense.cancellation_month = cancellation_month
    expense.charged_when_cancelled = charged_this_month
    expense.cancelled_at = now
    expense.cancelled_by_id = cancelled_by_id
    expense.updated_at = now
    db.commit()
    db.refresh(expense)
    return expense