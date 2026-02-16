from uuid import UUID

from sqlalchemy.orm import Session, joinedload, subqueryload

from app.models.user import User, UserRole
from app.models.department import Department
from app.models.company import Company
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password


def get_all(db: Session) -> list[User]:
    """Lista todos os usuários com departments e companies."""
    # Usar subqueryload para relacionamentos many-to-many evita duplicatas
    return db.query(User).options(
        subqueryload(User.departments),
        subqueryload(User.companies),
    ).all()


def get_by_id(db: Session, user_id: UUID) -> User | None:
    """Busca usuário por ID com departments e companies."""
    return db.query(User).options(
        subqueryload(User.departments),
        subqueryload(User.companies),
    ).filter(User.id == user_id).first()


def get_by_email(db: Session, email: str) -> User | None:
    """Busca usuário por email"""
    return db.query(User).filter(User.email == email).first()


def create(db: Session, data: UserCreate) -> User:
    """Cria novo usuário"""
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        phone=data.phone,
    )
    
    if data.department_ids:
        departments = db.query(Department).filter(
            Department.id.in_(data.department_ids)
        ).all()
        user.departments = departments

    if data.company_ids and data.role in (UserRole.LEADER, UserRole.FINANCE_ADMIN):
        companies = db.query(Company).filter(
            Company.id.in_(data.company_ids)
        ).all()
        user.companies = companies
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update(db: Session, user: User, data: UserUpdate) -> User:
    """Atualiza usuário existente"""
    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email
    if data.password is not None:
        user.password_hash = hash_password(data.password)
    if data.role is not None:
        user.role = data.role
    if data.phone is not None:
        user.phone = data.phone
    if data.is_active is not None:
        user.is_active = data.is_active
    
    if data.department_ids is not None:
        departments = db.query(Department).filter(
            Department.id.in_(data.department_ids)
        ).all()
        user.departments = departments

    if data.company_ids is not None and user.role in (UserRole.LEADER, UserRole.FINANCE_ADMIN):
        companies = db.query(Company).filter(
            Company.id.in_(data.company_ids)
        ).all()
        user.companies = companies
    elif data.role is not None and data.role not in (UserRole.LEADER, UserRole.FINANCE_ADMIN):
        user.companies = []
    
    db.commit()
    db.refresh(user)
    return user


def delete(db: Session, user: User) -> User:
    """Desativa usuário (soft delete)"""
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user