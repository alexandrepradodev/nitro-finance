from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def get_all(db: Session) -> list[Category]:
    """Lista todas as categorias"""
    return db.query(Category).all()


def get_by_id(db: Session, category_id: UUID) -> Category | None:
    """Busca categoria por ID"""
    return db.query(Category).filter(Category.id == category_id).first()


def get_by_name(db: Session, name: str) -> Category | None:
    """Busca categoria por nome (case-insensitive)"""
    return db.query(Category).filter(func.lower(Category.name) == func.lower(name)).first()


def create(db: Session, data: CategoryCreate) -> Category:
    """Cria nova categoria"""
    category = Category(name=data.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update(db: Session, category: Category, data: CategoryUpdate) -> Category:
    """Atualiza categoria existente"""
    if data.name is not None:
        category.name = data.name
    if data.is_active is not None:
        category.is_active = data.is_active
    
    db.commit()
    db.refresh(category)
    return category


def delete(db: Session, category: Category) -> Category:
    """Desativa categoria (soft delete)"""
    category.is_active = False
    db.commit()
    db.refresh(category)
    return category