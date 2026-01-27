from uuid import UUID

from sqlalchemy.orm import Session

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate


def get_all(db: Session) -> list[Department]:
    """Lista todos os setores"""
    return db.query(Department).all()


def get_by_id(db: Session, department_id: UUID) -> Department | None:
    """Busca setor por ID"""
    return db.query(Department).filter(Department.id == department_id).first()


def get_by_name_and_company(db: Session, name: str, company_id: UUID) -> Department | None:
    """Busca setor por nome dentro de uma empresa"""
    return db.query(Department).filter(
        Department.name == name,
        Department.company_id == company_id
    ).first()


def get_by_company(db: Session, company_id: UUID) -> list[Department]:
    """Lista setores de uma empresa"""
    return db.query(Department).filter(Department.company_id == company_id).all()


def create(db: Session, data: DepartmentCreate) -> Department:
    """Cria novo setor"""
    department = Department(
        name=data.name,
        company_id=data.company_id
    )
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


def update(db: Session, department: Department, data: DepartmentUpdate) -> Department:
    """Atualiza setor existente"""
    if data.name is not None:
        department.name = data.name
    if data.company_id is not None:
        department.company_id = data.company_id
    if data.is_active is not None:
        department.is_active = data.is_active
    
    db.commit()
    db.refresh(department)
    return department


def delete(db: Session, department: Department) -> Department:
    """Desativa setor (soft delete)"""
    department.is_active = False
    db.commit()
    db.refresh(department)
    return department