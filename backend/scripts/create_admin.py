#!/usr/bin/env python3
"""
Script para criar usuário System Admin.

Uso:
    python scripts/create_admin.py
"""

import sys
from pathlib import Path

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.services.user_service import get_by_email, create
from app.schemas.user import UserCreate
from app.models.user import UserRole


def main():
    """Cria usuário System Admin."""
    db = SessionLocal()
    
    try:
        email = "alexandre.prado@nitrocompany.co"
        password = "12212008"
        name = "Alexandre Prado"
        
        # Verificar se usuário já existe
        existing_user = get_by_email(db, email)
        if existing_user:
            print(f"❌ Usuário com email '{email}' já existe!")
            print(f"   ID: {existing_user.id}")
            print(f"   Nome: {existing_user.name}")
            print(f"   Role: {existing_user.role}")
            return
        
        # Criar usuário
        print(f"📦 Criando usuário System Admin...")
        user = create(db, UserCreate(
            name=name,
            email=email,
            password=password,
            role=UserRole.SYSTEM_ADMIN,
            company_ids=[],
            department_ids=[]
        ))
        
        print(f"✅ Usuário criado com sucesso!")
        print(f"   ID: {user.id}")
        print(f"   Nome: {user.name}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role}")
        print(f"\n🔐 Credenciais de acesso:")
        print(f"   Email: {email}")
        print(f"   Senha: {password}")
        
    except Exception as e:
        print(f"❌ Erro ao criar usuário: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
