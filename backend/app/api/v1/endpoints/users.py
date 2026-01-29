from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserWithDepartmentsResponse
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])

# Apenas admins podem gerenciar usuários
admin_only = require_roles([UserRole.FINANCE_ADMIN, UserRole.SYSTEM_ADMIN])


@router.get("/me", response_model=UserWithDepartmentsResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retorna os dados do usuário logado"""
    return current_user


@router.get("", response_model=list[UserWithDepartmentsResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Lista todos os usuários"""
    return user_service.get_all(db)


@router.get("/{user_id}", response_model=UserWithDepartmentsResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Busca usuário por ID"""
    user = user_service.get_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Cria novo usuário"""
    existing = user_service.get_by_email(db, data.email)
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário com este email"
        )
    
    return user_service.create(db, data)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Atualiza usuário"""
    user = user_service.get_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Verifica email duplicado
    if data.email and data.email != user.email:
        existing = user_service.get_by_email(db, data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um usuário com este email"
            )
    
    return user_service.update(db, user, data)


@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Desativa usuário"""
    user = user_service.get_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Não permite desativar a si mesmo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode desativar sua própria conta"
        )
    
    return user_service.delete(db, user)