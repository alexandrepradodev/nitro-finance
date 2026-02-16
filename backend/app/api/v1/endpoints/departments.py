from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles, get_current_user
from app.core.permissions import _role_value
from app.models.user import User, UserRole
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentWithCompanyResponse
from app.services import department_service, company_service

router = APIRouter(prefix="/departments", tags=["Departments"])

# Apenas admins podem gerenciar setores
admin_only = require_roles([UserRole.FINANCE_ADMIN, UserRole.SYSTEM_ADMIN])


@router.get("/me", response_model=list[DepartmentWithCompanyResponse])
def get_my_departments(
    company_id: UUID | None = Query(None, description="Filtrar por empresa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna setores do escopo do usuário logado"""
    role_val = _role_value(current_user.role)
    
    if role_val in (UserRole.SYSTEM_ADMIN.value, UserRole.FINANCE_ADMIN.value):
        # System Admin e Finance Admin têm acesso a tudo
        if company_id:
            return department_service.get_by_company(db, company_id)
        return department_service.get_all(db)
    elif role_val == UserRole.LEADER.value:
        company_ids = [c.id for c in current_user.companies] if current_user.companies else []
        if not company_ids:
            return []
        # Retornar todos os departamentos das empresas do líder
        all_depts = department_service.get_all(db)
        filtered = [d for d in all_depts if d.company_id in company_ids]
        if company_id:
            if company_id not in company_ids:
                return []
            filtered = [d for d in filtered if d.company_id == company_id]
        return filtered
    return []


@router.get("", response_model=list[DepartmentWithCompanyResponse])
def list_departments(
    company_id: UUID | None = Query(None, description="Filtrar por empresa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Lista todos os setores (pode filtrar por empresa)"""
    if company_id:
        return department_service.get_by_company(db, company_id)
    return department_service.get_all(db)


@router.get("/{department_id}", response_model=DepartmentWithCompanyResponse)
def get_department(
    department_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Busca setor por ID"""
    department = department_service.get_by_id(db, department_id)
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setor não encontrado"
        )
    
    return department





@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Cria novo setor"""
    # Verifica se a empresa existe
    company = company_service.get_by_id(db, data.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empresa não encontrada"
        )
    
    # Verifica duplicado na mesma empresa
    existing = department_service.get_by_name_and_company(db, data.name, data.company_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um setor com este nome nesta empresa"
        )
    
    return department_service.create(db, data)

@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: UUID,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Atualiza setor"""
    department = department_service.get_by_id(db, department_id)
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setor não encontrado"
        )
    
    # Se está mudando a empresa, verifica se existe
    if data.company_id and data.company_id != department.company_id:
        company = company_service.get_by_id(db, data.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empresa não encontrada"
            )
    
    # Verifica duplicado
    company_id = data.company_id or department.company_id
    name = data.name or department.name
    
    if data.name or data.company_id:
        existing = department_service.get_by_name_and_company(db, name, company_id)
        if existing and existing.id != department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um setor com este nome nesta empresa"
            )
    
    return department_service.update(db, department, data)


@router.delete("/{department_id}", response_model=DepartmentResponse)
def delete_department(
    department_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Desativa setor"""
    department = department_service.get_by_id(db, department_id)
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setor não encontrado"
        )
    
    return department_service.delete(db, department)