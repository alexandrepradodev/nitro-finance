from uuid import UUID

from sqlalchemy.orm import Session

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


def get_all(db: Session) -> list[Company]:
    """Lista todas as empresas"""
    return db.query(Company).all()


def get_by_id(db: Session, company_id: UUID) -> Company | None:
    """Busca empresa por ID"""
    return db.query(Company).filter(Company.id == company_id).first()


def get_by_name(db: Session, name: str) -> Company | None:
    """Busca empresa por nome"""
    return db.query(Company).filter(Company.name == name).first()


def create(db: Session, data: CompanyCreate) -> Company:
    """Cria nova empresa"""
    company = Company(name=data.name)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def update(db: Session, company: Company, data: CompanyUpdate) -> Company:
    """Atualiza empresa existente"""
    if data.name is not None:
        company.name = data.name
    if data.is_active is not None:
        company.is_active = data.is_active
    
    db.commit()
    db.refresh(company)
    return company


def delete(db: Session, company: Company) -> Company:
    """Desativa empresa (soft delete)"""
    company.is_active = False
    db.commit()
    db.refresh(company)
    return company