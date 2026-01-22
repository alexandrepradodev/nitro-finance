from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.services import company_service

router = APIRouter(prefix="/companies", tags=["Companies"])

# Apenas admins podem gerenciar empresas
admin_only = require_roles([UserRole.FINANCE_ADMIN, UserRole.SYSTEM_ADMIN])


@router.get("", response_model=list[CompanyResponse])
def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Lista todas as empresas"""
    return company_service.get_all(db)


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Busca empresa por ID"""
    company = company_service.get_by_id(db, company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )
    
    return company


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Cria nova empresa"""
    existing = company_service.get_by_name(db, data.name)
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma empresa com este nome"
        )
    
    return company_service.create(db, data)


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: UUID,
    data: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Atualiza empresa"""
    company = company_service.get_by_id(db, company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )
    
    if data.name and data.name != company.name:
        existing = company_service.get_by_name(db, data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma empresa com este nome"
            )
    
    return company_service.update(db, company, data)


@router.delete("/{company_id}", response_model=CompanyResponse)
def delete_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Desativa empresa"""
    company = company_service.get_by_id(db, company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )
    
    return company_service.delete(db, company)