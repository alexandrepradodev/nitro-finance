from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.permissions import can_access_expense, can_approve_expense
from app.models.user import User, UserRole
from app.schemas.expense_validation import (
    ExpenseValidationResponse,
    ExpenseValidationWithExpenseResponse,
    ExpenseBasic,
    CompanyBasic,
    DepartmentBasic,
    UserBasic,
    RejectRequest,
)
from app.services import expense_validation_service
from app.models.expense_validation import ValidationStatus

router = APIRouter(prefix="/expense-validations", tags=["Expense Validations"])

# Apenas admins podem executar tarefas administrativas
admin_only = require_roles([UserRole.FINANCE_ADMIN, UserRole.SYSTEM_ADMIN])


@router.get("/pending", response_model=list[ExpenseValidationWithExpenseResponse])
def list_pending_validations(
    month: date | None = Query(None, description="Filtrar por mês (primeiro dia do mês)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista validações pendentes no escopo do usuário (empresa + responsável).
    """
    validations = expense_validation_service.get_pending(db, month, current_user=current_user)
    return validations


@router.get("/history", response_model=list[ExpenseValidationWithExpenseResponse])
def get_validation_history(
    status: ValidationStatus | None = Query(None, description="Filtrar por status"),
    month: date | None = Query(None, description="Filtrar por mês (primeiro dia do mês)"),
    expense_id: UUID | None = Query(None, description="Filtrar por despesa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista histórico de validações no escopo do usuário.
    Filtros opcionais: status, mês, despesa.
    """
    validations = expense_validation_service.get_history(
        db, status, month, expense_id, current_user=current_user
    )
    return validations


@router.get("/predicted", response_model=list[ExpenseValidationWithExpenseResponse])
def get_predicted_validations(
    month: date = Query(..., description="Mês futuro para previsão (primeiro dia do mês)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista validações previstas para um mês futuro.
    Retorna despesas que teriam validação naquele mês baseado na periodicidade.
    Não cria registros no banco.
    Apenas despesas ATIVAS são consideradas (canceladas não aparecem).
    """
    from datetime import datetime
    from uuid import uuid4
    
    # Validar que é um mês futuro
    today = datetime.now().date()
    first_day_target = month.replace(day=1)
    first_day_current = today.replace(day=1)
    
    if first_day_target <= first_day_current:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este endpoint é apenas para meses futuros. Use /pending ou /history para meses passados/atuais."
        )
    
    predicted = expense_validation_service.get_predicted_validations(db, first_day_target, current_user=current_user)
    
    # Converter para formato de resposta (criar objetos temporários similares a ExpenseValidation)
    result = []
    for item in predicted:
        expense = item["expense"]
        validation_month = item["validation_month"]
        
        # Criar objeto temporário similar a ExpenseValidation mas sem ID
        # Usar ExpenseValidationWithExpenseResponse com campos adaptados
        # Garantir que os relacionamentos foram carregados
        currency_str = expense.currency.value if hasattr(expense.currency, 'value') else str(expense.currency)
        status_str = expense.status.value if hasattr(expense.status, 'value') else str(expense.status)
        
        company_basic = None
        if expense.company:
            company_basic = CompanyBasic(
                id=expense.company.id,
                name=expense.company.name
            )
        
        department_basic = None
        if expense.department:
            department_basic = DepartmentBasic(
                id=expense.department.id,
                name=expense.department.name
            )
        
        owner_basic = None
        if expense.owner:
            owner_basic = UserBasic(
                id=expense.owner.id,
                name=expense.owner.name,
                email=expense.owner.email
            )
        
        expense_basic = ExpenseBasic(
            id=expense.id,
            code=expense.code,
            service_name=expense.service_name,
            value=expense.value,
            currency=currency_str,
            value_brl=expense.value_brl,
            status=status_str,
            department_id=expense.department_id,
            company=company_basic,
            department=department_basic,
            owner=owner_basic
        )
        
        # Criar resposta temporária
        validation_response = ExpenseValidationWithExpenseResponse(
            id=None,  # Não tem ID pois não existe no banco
            expense_id=expense.id,
            validator_id=None,
            validation_month=validation_month,
            status=ValidationStatus.PENDING,
            validated_at=None,
            is_overdue=False,
            is_predicted=True,
            created_at=None,
            updated_at=None,
            expense=expense_basic,
            validator=None
        )
        
        result.append(validation_response)
    
    return result


@router.get("/{validation_id}", response_model=ExpenseValidationWithExpenseResponse)
def get_validation(
    validation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Busca validação específica (apenas se estiver no escopo do usuário).
    """
    validation = expense_validation_service.get_by_id(db, validation_id)
    
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validação não encontrada"
        )
    if not can_access_expense(current_user, validation.expense):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a esta validação"
        )
    return validation


@router.post("/{validation_id}/approve", response_model=ExpenseValidationResponse)
def approve_validation(
    validation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aprova validação (apenas se a despesa estiver no escopo do usuário).
    """
    validation = expense_validation_service.get_by_id(db, validation_id)
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validação não encontrada"
        )
    if not can_approve_expense(current_user, validation.expense):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para aprovar esta validação"
        )
    try:
        validation = expense_validation_service.approve(db, validation_id, current_user.id)
        return validation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{validation_id}/reject", response_model=ExpenseValidationResponse)
def reject_validation(
    validation_id: UUID,
    body: RejectRequest = Body(default=RejectRequest(charged_this_month=False)),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rejeita validação (cancela despesa). Apenas se a despesa estiver no escopo do usuário.
    Body opcional: charged_this_month (se a despesa já foi processada no mês, valor conta no dashboard).
    """
    validation = expense_validation_service.get_by_id(db, validation_id)
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validação não encontrada"
        )
    if not can_approve_expense(current_user, validation.expense):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para rejeitar esta validação"
        )
    charged = body.charged_this_month
    try:
        validation = expense_validation_service.reject(
            db, validation_id, current_user.id, charged_this_month=charged
        )
        return validation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/mark-overdue", status_code=status.HTTP_200_OK)
def mark_overdue_validations_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Marca validações pendentes como atrasadas se passaram 4 dias do início do mês.
    Apenas admins podem executar.
    """
    count = expense_validation_service.mark_overdue_validations(db)
    return {"message": f"{count} validações marcadas como atrasadas", "count": count}


@router.post("/create-monthly", status_code=status.HTTP_201_CREATED)
def create_monthly_validations_endpoint(
    month: date | None = Query(None, description="Mês para criar validações (primeiro dia do mês). Se não fornecido, usa o mês atual."),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Cria validações mensais para todas despesas recorrentes ativas baseado na periodicidade.
    Apenas admins podem executar.
    Se month não for fornecido, usa o primeiro dia do mês atual.
    """
    from datetime import datetime
    
    if month is None:
        today = datetime.now().date()
        month = today.replace(day=1)
    else:
        month = month.replace(day=1)
    
    validations = expense_validation_service.create_monthly_validations(db, month)
    
    return {
        "message": f"{len(validations)} validações criadas para o mês {month.strftime('%Y-%m')}",
        "count": len(validations),
        "month": month.isoformat()
    }
