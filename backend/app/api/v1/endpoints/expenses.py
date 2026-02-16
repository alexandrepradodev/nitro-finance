import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.permissions import (
    get_expense_scope_params,
    can_access_expense,
    can_create_expense_in_company,
    _role_value as _perm_role_value,
)
from app.models.user import User, UserRole
from app.models.expense import ExpenseStatus, ExpenseType
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseWithRelationsResponse, ExpenseCancelRequest
from app.services import expense_service, expense_validation_service, exchange_service
from app.services import category_service, company_service, department_service, user_service

router = APIRouter(prefix="/expenses", tags=["Expenses"])

# Apenas admins podem gerenciar todas as despesas
admin_only = require_roles([UserRole.FINANCE_ADMIN, UserRole.SYSTEM_ADMIN])


def _normalize_list(value: list | None) -> list | None:
    """Retorna None se lista vazia, senão a própria lista."""
    if value is None or len(value) == 0:
        return None
    return value


@router.get("", response_model=list[ExpenseWithRelationsResponse])
def list_expenses(
    company_ids: list[UUID] | None = Query(None, description="Filtrar por empresas"),
    department_ids: list[UUID] | None = Query(None, description="Filtrar por setores"),
    owner_ids: list[UUID] | None = Query(None, description="Filtrar por responsáveis"),
    category_ids: list[UUID] | None = Query(None, description="Filtrar por categorias"),
    status: list[ExpenseStatus] | None = Query(None, description="Filtrar por status"),
    expense_type: list[ExpenseType] | None = Query(None, description="Filtrar por tipo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista despesas com escopo por role (empresa + responsável/created_by)."""
    company_ids = _normalize_list(company_ids)
    department_ids = _normalize_list(department_ids)
    owner_ids = _normalize_list(owner_ids)
    category_ids = _normalize_list(category_ids)
    statuses = _normalize_list(status)
    expense_types = _normalize_list(expense_type)

    scope = get_expense_scope_params(current_user)
    scope_company_ids = scope["company_ids"]
    scope_owner_ids = scope["owner_ids"]
    scope_created_by_id = scope["created_by_id"]
    scope_department_ids = scope.get("department_ids")

    if scope_company_ids is not None and len(scope_company_ids) == 0:
        return []

    # Validar filtros contra escopo do usuário
    role_val = _perm_role_value(current_user.role)
    
    # System Admin e Finance Admin têm acesso a tudo, não precisam validação
    if role_val in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
        pass  # Não valida, permite tudo
    elif role_val == UserRole.LEADER.value:
        # Para líder, validar apenas que company_ids estão no escopo
        # department_ids e owner_ids não precisam validação pois líder vê todos das suas empresas
        if company_ids:
            invalid_companies = [c for c in company_ids if c not in (scope_company_ids or [])]
            if invalid_companies:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Você não tem acesso às empresas: {', '.join(str(c) for c in invalid_companies)}"
                )

    # Aplicar filtros de escopo
    final_company_ids = scope_company_ids
    if company_ids:
        if scope_company_ids is not None:
            # Intersectar filtros do usuário com escopo
            final_company_ids = [c for c in company_ids if c in scope_company_ids]
        elif role_val in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
            # Admins podem usar qualquer filtro
            final_company_ids = company_ids

    # Para líder, owner_ids e department_ids não são filtrados pelo escopo (None significa sem filtro)
    # Para outros roles, aplicar escopo se existir
    final_owner_ids = owner_ids
    if owner_ids and scope_owner_ids is not None:
        # Intersectar filtros do usuário com escopo
        final_owner_ids = [o for o in owner_ids if o in scope_owner_ids]
    elif not owner_ids:
        # Se não há filtro do usuário, usar escopo (pode ser None)
        final_owner_ids = scope_owner_ids

    final_department_ids = department_ids
    if department_ids and scope_department_ids is not None:
        # Intersectar filtros do usuário com escopo
        final_department_ids = [d for d in department_ids if d in scope_department_ids]
    elif not department_ids:
        # Se não há filtro do usuário, usar escopo (pode ser None)
        final_department_ids = scope_department_ids

    expenses = expense_service.get_filtered(
        db,
        company_ids=final_company_ids,
        department_ids=final_department_ids,
        owner_ids=final_owner_ids,
        created_by_id=scope_created_by_id,
        category_ids=category_ids,
        statuses=statuses,
        expense_types=expense_types,
    )
    return expenses


@router.get("/{expense_id}", response_model=ExpenseWithRelationsResponse)
def get_expense(
    expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca despesa por ID com relacionamentos"""
    expense = expense_service.get_by_id(db, expense_id)
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Despesa não encontrada"
        )
    if not can_access_expense(current_user, expense):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a esta despesa"
        )
    return expense


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria nova despesa (qualquer autenticado; responsável deve ser líder ou admin)."""
    
    # Valida categoria
    category = category_service.get_by_id(db, data.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Categoria não encontrada"
        )
    
    # Valida empresa
    company = company_service.get_by_id(db, data.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empresa não encontrada"
        )
    
    # Valida setor
    department = department_service.get_by_id(db, data.department_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setor não encontrado"
        )
    
    owner = user_service.get_by_id(db, data.owner_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Responsável não encontrado"
        )
    
    # Verificar se o responsável pertence à empresa da despesa
    # System Admin e Finance Admin podem ser responsáveis em qualquer empresa
    owner_role = _perm_role_value(owner.role)
    if owner_role not in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
        owner_company_ids = [c.id for c in owner.companies] if owner.companies else []
        if data.company_id not in owner_company_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O responsável selecionado não pertence à empresa escolhida"
            )
    
    if not can_create_expense_in_company(current_user, data.company_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para criar despesa nesta empresa"
        )
    # Responsável = validador: se approver_id não vier, usa owner_id
    approver_id = data.approver_id if data.approver_id is not None else data.owner_id
    data = data.model_copy(update={"approver_id": approver_id})

    # Converte para BRL
    try:
        currency_str = data.currency.value if hasattr(data.currency, "value") else str(data.currency)
        value_brl, exchange_rate, exchange_rate_date = exchange_service.convert_to_brl(
            data.value, currency_str
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
    except Exception as e:
        logging.exception("Erro ao converter valor para BRL")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro na cotação: {e!s}"
        )

    try:
        expense = expense_service.create(
            db=db,
            data=data,
            value_brl=value_brl,
            exchange_rate=exchange_rate,
            exchange_rate_date=exchange_rate_date,
            created_by_id=current_user.id,
        )
        expense_validation_service.create_validation_for_creation_month(db, expense)
        return expense
    except IntegrityError as e:
        logging.warning("IntegrityError ao criar despesa: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dados inválidos ou conflito (ex.: setor não pertence à empresa)."
        )
    except Exception as e:
        logging.exception("Erro ao criar despesa")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: UUID,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza despesa (quem tem acesso à despesa pode editar)."""
    expense = expense_service.get_by_id(db, expense_id)
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Despesa não encontrada"
        )
    if not can_access_expense(current_user, expense):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a esta despesa"
        )
    
    # Se mudou valor ou moeda, recalcula value_brl
    value_brl = None
    exchange_rate = None
    exchange_rate_date = None
    
    if data.value is not None or data.currency is not None:
        new_value = data.value if data.value is not None else expense.value
        new_currency = data.currency if data.currency is not None else expense.currency
        
        try:
            value_brl, exchange_rate, exchange_rate_date = exchange_service.convert_to_brl(
                new_value, new_currency.value
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e)
            )
    
    # Responsável = validador: ao alterar owner_id, forçar approver_id = owner_id
    if data.owner_id is not None:
        data = data.model_copy(update={"approver_id": data.owner_id})
    try:
        return expense_service.update(
            db=db,
            expense=expense,
            data=data,
            value_brl=value_brl,
            exchange_rate=exchange_rate,
            exchange_rate_date=exchange_rate_date
        )
    except IntegrityError as e:
        logging.warning("IntegrityError ao atualizar despesa: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dados inválidos ou conflito (ex.: setor não pertence à empresa)."
        )
    except Exception as e:
        logging.exception("Erro ao atualizar despesa")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{expense_id}/cancel", response_model=ExpenseResponse)
def cancel_expense(
    expense_id: UUID,
    body: ExpenseCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancela despesa (quem tem acesso pode cancelar)."""
    expense = expense_service.get_by_id(db, expense_id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Despesa não encontrada"
        )
    if not can_access_expense(current_user, expense):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a esta despesa"
        )
    cancel_month = body.cancellation_month
    if cancel_month is None:
        cancel_month = date.today().replace(day=1)
    return expense_service.cancel_with_info(
        db, expense,
        charged_this_month=body.charged_this_month,
        cancellation_month=cancel_month,
        cancelled_by_id=current_user.id,
    )


@router.delete("/{expense_id}", response_model=ExpenseResponse)
def delete_expense(
    expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Desativa despesa (quem tem acesso pode deletar)."""
    expense = expense_service.get_by_id(db, expense_id)
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Despesa não encontrada"
        )
    if not can_access_expense(current_user, expense):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a esta despesa"
        )
    return expense_service.delete(db, expense)