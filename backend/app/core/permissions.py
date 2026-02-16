"""Helpers for expense scope by role (company + owner/created_by)."""
from uuid import UUID

from app.models.user import User, UserRole
from app.models.expense import Expense


KNOWN_ROLES = frozenset({
    UserRole.SYSTEM_ADMIN.value,
    UserRole.FINANCE_ADMIN.value,
    UserRole.LEADER.value,
})


def _role_value(role) -> str:
    """Normaliza role para string (enum ou string do DB)."""
    return role.value if hasattr(role, "value") else str(role)


def get_expense_scope_params(current_user: User) -> dict:
    """
    Returns scope parameters for listing expenses: company_ids, owner_ids, created_by_id, department_ids.
    None for a key means no filter on that dimension.
    Used by list_expenses and dashboard to restrict by role.
    """
    role_val = (_role_value(current_user.role) or "").strip()
    if not role_val or role_val not in KNOWN_ROLES:
        # Fallback seguro: nenhum acesso para roles desconhecidos
        return {"company_ids": [], "owner_ids": [], "created_by_id": current_user.id, "department_ids": []}

    if role_val in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
        # System Admin e Finance Admin têm acesso total
        return {"company_ids": None, "owner_ids": None, "created_by_id": None, "department_ids": None}

    if role_val == UserRole.LEADER.value:
        company_ids = [c.id for c in current_user.companies] if current_user.companies else []
        if not company_ids:
            return {"company_ids": [], "owner_ids": None, "created_by_id": None, "department_ids": None}
        return {"company_ids": company_ids, "owner_ids": None, "created_by_id": None, "department_ids": None}

    # Fallback seguro: nenhum acesso para roles desconhecidos
    return {"company_ids": [], "owner_ids": [], "created_by_id": current_user.id, "department_ids": []}


def can_access_expense(current_user: User, expense: Expense) -> bool:
    """True if current_user is allowed to view/edit the given expense."""
    if _role_value(current_user.role) in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
        # System Admin e Finance Admin têm acesso total
        return True
    if _role_value(current_user.role) == UserRole.LEADER.value:
        company_ids = [c.id for c in current_user.companies] if current_user.companies else []
        if not company_ids:
            return False
        return expense.company_id in company_ids
    # User: only if they created it
    return expense.created_by_id == current_user.id


def can_create_expense_in_company(current_user: User, company_id: UUID) -> bool:
    """True if current_user can create an expense in the given company."""
    if _role_value(current_user.role) in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
        # System Admin e Finance Admin podem criar em qualquer empresa
        return True
    if _role_value(current_user.role) == UserRole.LEADER.value:
        company_ids = [c.id for c in current_user.companies] if current_user.companies else []
        return company_id in company_ids
    # User can create in any company (they assign owner to leader/admin)
    return True


def can_approve_expense(current_user: User, expense: Expense) -> bool:
    """True if current_user is allowed to approve/reject the given expense."""
    if _role_value(current_user.role) in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
        # System Admin e Finance Admin podem aprovar tudo
        return True
    if _role_value(current_user.role) == UserRole.LEADER.value:
        # Leader só pode aprovar despesas onde é o responsável (owner)
        company_ids = [c.id for c in current_user.companies] if current_user.companies else []
        if not company_ids:
            return False
        return (
            expense.owner_id == current_user.id
            and expense.company_id in company_ids
        )
    # Outros roles não podem aprovar
    return False
