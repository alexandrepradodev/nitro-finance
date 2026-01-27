from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["Categories"])

# Apenas admins podem gerenciar categorias
admin_only = require_roles([UserRole.FINANCE_ADMIN, UserRole.SYSTEM_ADMIN])


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Lista todas as categorias"""
    return category_service.get_all(db)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Busca categoria por ID"""
    category = category_service.get_by_id(db, category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada"
        )
    
    return category


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Cria nova categoria"""
    existing = category_service.get_by_name(db, data.name)
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma categoria com este nome"
        )
    
    return category_service.create(db, data)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Atualiza categoria"""
    category = category_service.get_by_id(db, category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada"
        )
    
    if data.name and data.name != category.name:
        existing = category_service.get_by_name(db, data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma categoria com este nome"
            )
    
    return category_service.update(db, category, data)


@router.delete("/{category_id}", response_model=CategoryResponse)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Desativa categoria"""
    category = category_service.get_by_id(db, category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada"
        )
    
    return category_service.delete(db, category)