from uuid import UUID
from datetime import date, datetime, timezone, timedelta

from sqlalchemy.orm import Session, joinedload, subqueryload
from sqlalchemy import and_

from app.models.expense_validation import ExpenseValidation, ValidationStatus
from app.models.expense import Expense, ExpenseStatus, ExpenseType, Periodicity
from app.models.user import User, UserRole
from app.schemas.expense_validation import ExpenseValidationCreate


def should_create_validation_for_month(expense: Expense, target_month: date) -> bool:
    """
    Determina se deve criar validação para um mês específico baseado na periodicidade.
    Validações começam no mês seguinte à criação da despesa.
    """
    if expense.expense_type != ExpenseType.RECURRING or not expense.periodicity:
        return False
    
    # Calcular meses desde a criação (usando primeiro dia do mês)
    expense_creation_month = expense.created_at.replace(day=1).date() if isinstance(expense.created_at, datetime) else expense.created_at.replace(day=1)
    target_first_day = target_month.replace(day=1)
    
    # Se a despesa foi criada no mesmo mês ou depois, não criar validação
    if target_first_day <= expense_creation_month:
        return False
    
    # Calcular diferença em meses
    months_since_creation = (target_first_day.year - expense_creation_month.year) * 12 + \
                            (target_first_day.month - expense_creation_month.month)
    
    # Primeira validação sempre no mês seguinte à criação
    if months_since_creation < 1:
        return False
    
    periodicity_months = {
        Periodicity.MONTHLY: 1,
        Periodicity.QUARTERLY: 3,
        Periodicity.SEMIANNUAL: 6,
        Periodicity.ANNUAL: 12
    }
    
    months_interval = periodicity_months.get(expense.periodicity, 1)
    
    # Verificar se o mês alvo corresponde ao intervalo de periodicidade
    # Para mensal: sempre criar
    # Para trimestral: criar a cada 3 meses (1, 4, 7, 10...)
    # Para semestral: criar a cada 6 meses (1, 7, 13...)
    # Para anual: criar a cada 12 meses (1, 13, 25...)
    return months_since_creation % months_interval == 0


def create_validation_for_creation_month(db: Session, expense: Expense) -> ExpenseValidation | None:
    """
    Cria uma validação para o mês em que a despesa foi criada, para que apareça
    na aba Validações daquele mês (recorrente ou única).
    Usa o mês atual do servidor (UTC) para evitar problemas de sessão/timezone.
    """
    first_day = datetime.now(timezone.utc).date().replace(day=1)

    existing = db.query(ExpenseValidation).filter(
        and_(
            ExpenseValidation.expense_id == expense.id,
            ExpenseValidation.validation_month == first_day,
        )
    ).first()
    if existing:
        return None

    validation = ExpenseValidation(
        expense_id=expense.id,
        validator_id=None,
        validation_month=first_day,
        status=ValidationStatus.PENDING,
        is_overdue=False,
    )
    db.add(validation)
    db.commit()
    db.refresh(validation)
    return validation


def create_monthly_validations(db: Session, month_date: date) -> list[ExpenseValidation]:
    """
    Cria validações para todas despesas recorrentes ativas do mês.
    Baseado na periodicidade da despesa.
    Não associa a nenhum validador inicialmente (validator_id = NULL).
    """
    # Primeiro dia do mês
    first_day = month_date.replace(day=1)
    
    # Buscar todas despesas recorrentes ativas
    active_expenses = db.query(Expense).filter(
        Expense.status == ExpenseStatus.ACTIVE,
        Expense.expense_type == ExpenseType.RECURRING
    ).all()
    
    validations = []
    
    for expense in active_expenses:
        # Verificar se deve criar validação para este mês baseado na periodicidade
        if not should_create_validation_for_month(expense, first_day):
            continue
        
        # Verificar se já existe validação para este mês
        existing = db.query(ExpenseValidation).filter(
            and_(
                ExpenseValidation.expense_id == expense.id,
                ExpenseValidation.validation_month == first_day
            )
        ).first()
        
        if not existing:
            validation = ExpenseValidation(
                expense_id=expense.id,
                validator_id=None,  # Não associar a nenhum validador inicialmente
                validation_month=first_day,
                status=ValidationStatus.PENDING,
                is_overdue=False
            )
            db.add(validation)
            validations.append(validation)
    
    db.commit()
    
    # Refresh todas as validações criadas
    for validation in validations:
        db.refresh(validation)
    
    return validations


def _role_value(role) -> str:
    """Normaliza role para string (enum ou string do DB)."""
    return role.value if hasattr(role, "value") else str(role)


def _validation_scope_filters(query, current_user: User):
    """Aplica filtro de escopo por role (empresa + owner/created_by)."""
    rv = _role_value(current_user.role)
    if rv in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
        # System Admin e Finance Admin têm acesso total
        return query
    query = query.join(Expense, ExpenseValidation.expense_id == Expense.id)
    if rv == UserRole.LEADER.value:
        company_ids = [c.id for c in current_user.companies] if current_user.companies else []
        if not company_ids:
            return query.filter(False)
        return query.filter(
            Expense.company_id.in_(company_ids)
        )
    return query.filter(Expense.created_by_id == current_user.id)


def get_pending(
    db: Session,
    month: date | None = None,
    current_user: User | None = None
) -> list[ExpenseValidation]:
    """
    Lista validações pendentes. Se current_user for informado, filtra pelo escopo do role.
    """
    query = db.query(ExpenseValidation).options(
        joinedload(ExpenseValidation.expense).subqueryload(Expense.company),
        joinedload(ExpenseValidation.expense).subqueryload(Expense.department),
        joinedload(ExpenseValidation.expense).subqueryload(Expense.owner),
        joinedload(ExpenseValidation.validator)
    ).filter(
        ExpenseValidation.status == ValidationStatus.PENDING
    )
    if current_user:
        query = _validation_scope_filters(query, current_user)
    if month:
        first_day = month.replace(day=1)
        query = query.filter(ExpenseValidation.validation_month == first_day)
    return query.order_by(ExpenseValidation.validation_month.desc()).all()


def mark_overdue_validations(db: Session) -> int:
    """
    Marca validações pendentes como atrasadas se passaram 4 dias do início do mês.
    Retorna o número de validações marcadas como atrasadas.
    """
    today = date.today()
    
    # Calcular data limite: 4 dias após o primeiro dia do mês atual
    first_day_current_month = today.replace(day=1)
    deadline = first_day_current_month + timedelta(days=4)
    
    # Se ainda estamos nos primeiros 4 dias do mês, não marcar nada como atrasado
    if today <= deadline:
        return 0
    
    # Buscar validações pendentes do mês atual que estão atrasadas
    overdue_validations = db.query(ExpenseValidation).filter(
        and_(
            ExpenseValidation.status == ValidationStatus.PENDING,
            ExpenseValidation.validation_month == first_day_current_month,
            ExpenseValidation.is_overdue == False
        )
    ).all()
    
    count = 0
    for validation in overdue_validations:
        validation.is_overdue = True
        validation.updated_at = datetime.now(timezone.utc)
        count += 1
    
    db.commit()
    return count


def get_by_expense_and_month(
    db: Session, 
    expense_id: UUID, 
    month: date
) -> ExpenseValidation | None:
    """Busca validação específica por despesa e mês"""
    first_day = month.replace(day=1)
    return db.query(ExpenseValidation).filter(
        and_(
            ExpenseValidation.expense_id == expense_id,
            ExpenseValidation.validation_month == first_day
        )
    ).first()


def get_by_id(db: Session, validation_id: UUID) -> ExpenseValidation | None:
    """Busca validação por ID"""
    return db.query(ExpenseValidation).options(
        joinedload(ExpenseValidation.expense).subqueryload(Expense.company),
        joinedload(ExpenseValidation.expense).subqueryload(Expense.department),
        joinedload(ExpenseValidation.expense).subqueryload(Expense.owner),
        joinedload(ExpenseValidation.validator)
    ).filter(
        ExpenseValidation.id == validation_id
    ).first()


def approve(db: Session, validation_id: UUID, validator_id: UUID) -> ExpenseValidation:
    """
    Aprova validação.
    Preenche validator_id com o usuário que está aprovando.
    """
    validation = get_by_id(db, validation_id)
    
    if not validation:
        raise ValueError("Validação não encontrada")
    
    if validation.status != ValidationStatus.PENDING:
        raise ValueError("Esta validação já foi processada")
    
    validation.status = ValidationStatus.APPROVED
    validation.validator_id = validator_id  # Preencher com quem está aprovando
    validation.validated_at = datetime.now(timezone.utc)
    validation.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(validation)
    
    return validation


def reject(
    db: Session,
    validation_id: UUID,
    validator_id: UUID,
    charged_this_month: bool = False,
) -> ExpenseValidation:
    """
    Rejeita validação.
    Muda o status da despesa para CANCELLED.
    Preenche cancellation_month (mês da validação) e charged_when_cancelled na despesa.
    """
    validation = get_by_id(db, validation_id)
    if not validation:
        raise ValueError("Validação não encontrada")
    if validation.status != ValidationStatus.PENDING:
        raise ValueError("Esta validação já foi processada")

    expense = db.query(Expense).filter(Expense.id == validation.expense_id).first()
    if not expense:
        raise ValueError("Despesa não encontrada")

    validation.status = ValidationStatus.REJECTED
    validation.validator_id = validator_id
    validation.validated_at = datetime.now(timezone.utc)
    validation.updated_at = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    expense.status = ExpenseStatus.CANCELLED
    expense.cancellation_month = validation.validation_month
    expense.charged_when_cancelled = charged_this_month
    expense.cancelled_at = now
    expense.cancelled_by_id = validator_id
    expense.updated_at = now

    db.commit()
    db.refresh(validation)
    return validation


def get_history(
    db: Session,
    status: ValidationStatus | None = None,
    month: date | None = None,
    expense_id: UUID | None = None,
    current_user: User | None = None
) -> list[ExpenseValidation]:
    """
    Lista histórico de validações. Se current_user for informado, filtra pelo escopo do role.
    """
    query = db.query(ExpenseValidation).options(
        joinedload(ExpenseValidation.expense).subqueryload(Expense.company),
        joinedload(ExpenseValidation.expense).subqueryload(Expense.department),
        joinedload(ExpenseValidation.expense).subqueryload(Expense.owner),
        joinedload(ExpenseValidation.validator)
    )
    if current_user:
        query = _validation_scope_filters(query, current_user)
    if status:
        query = query.filter(ExpenseValidation.status == status)
    if month:
        first_day = month.replace(day=1)
        query = query.filter(ExpenseValidation.validation_month == first_day)
    if expense_id:
        query = query.filter(ExpenseValidation.expense_id == expense_id)
    return query.order_by(ExpenseValidation.validation_month.desc(), ExpenseValidation.created_at.desc()).all()


def get_all_for_expense(db: Session, expense_id: UUID) -> list[ExpenseValidation]:
    """Lista todas validações de uma despesa"""
    return db.query(ExpenseValidation).filter(
        ExpenseValidation.expense_id == expense_id
    ).order_by(ExpenseValidation.validation_month.desc()).all()


def get_predicted_validations(
    db: Session,
    target_month: date,
    current_user: User | None = None
) -> list[dict]:
    """
    Retorna validações previstas para um mês futuro.
    Não cria registros no banco, apenas calcula quais despesas teriam validação.
    IMPORTANTE: Apenas despesas com status ACTIVE são consideradas.
    Despesas canceladas (CANCELLED) ou com outros status não aparecem.
    Se current_user for informado, filtra pelo escopo do role.
    Retorna lista de dicionários com dados da despesa e mês previsto.
    """
    from app.core.permissions import get_expense_scope_params
    
    first_day = target_month.replace(day=1)
    
    # Buscar APENAS despesas recorrentes ATIVAS (não canceladas)
    # Filtro explícito: status == ACTIVE garante que canceladas não aparecem
    query = db.query(Expense).options(
        joinedload(Expense.category),
        joinedload(Expense.company),
        joinedload(Expense.department),
        joinedload(Expense.owner),
        joinedload(Expense.approver)
    ).filter(
        Expense.status == ExpenseStatus.ACTIVE,  # Apenas ativas
        Expense.expense_type == ExpenseType.RECURRING
    )
    
    # Aplicar filtros de escopo se current_user for fornecido
    if current_user:
        scope = get_expense_scope_params(current_user)
        scope_company_ids = scope["company_ids"]
        scope_owner_ids = scope["owner_ids"]
        scope_department_ids = scope.get("department_ids")
        
        # Se company_ids está vazio, retornar lista vazia
        if scope_company_ids is not None and len(scope_company_ids) == 0:
            return []
        
        # Aplicar filtros de escopo
        # Para líder, apenas company_ids é filtrado (owner_ids e department_ids são None)
        if scope_company_ids is not None:
            query = query.filter(Expense.company_id.in_(scope_company_ids))
        if scope_owner_ids is not None:
            query = query.filter(Expense.owner_id.in_(scope_owner_ids))
        if scope_department_ids is not None:
            query = query.filter(Expense.department_id.in_(scope_department_ids))
    
    active_expenses = query.all()
    
    predicted = []
    
    for expense in active_expenses:
        # Verificar se deve ter validação para este mês baseado na periodicidade
        if should_create_validation_for_month(expense, first_day):
            # Verificar se já existe validação criada (se já foi criada, não é mais "prevista")
            existing = db.query(ExpenseValidation).filter(
                and_(
                    ExpenseValidation.expense_id == expense.id,
                    ExpenseValidation.validation_month == first_day
                )
            ).first()
            
            if not existing:
                predicted.append({
                    "expense": expense,
                    "validation_month": first_day,
                    "is_predicted": True
                })
    
    return predicted
