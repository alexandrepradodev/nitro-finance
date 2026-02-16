#!/usr/bin/env python3
"""
Script de seed para criar despesas de teste criadas em janeiro e suas validações.

Uso:
    python scripts/seed_expenses.py
    python scripts/seed_expenses.py --month 2026-01 --validation-month 2026-02 --count 20
    python scripts/seed_expenses.py --skip-existing
"""

import sys
import argparse
from pathlib import Path
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import SessionLocal
from app.models.expense import Expense, ExpenseType, ExpenseStatus, Periodicity, Currency, PaymentMethod
from app.models.expense_validation import ExpenseValidation, ValidationStatus
from app.models.user import UserRole
from app.services.expense_service import create as create_expense
from app.services.expense_validation_service import should_create_validation_for_month
from app.services.company_service import get_by_name, create as create_company
from app.services.department_service import get_by_name_and_company, create as create_department
from app.services.category_service import get_by_name, create as create_category
from app.services.user_service import get_by_email, create as create_user
from app.services.exchange_service import get_usd_to_brl_rate_sync, USD_BRL_FALLBACK_RATE
from app.schemas.expense import ExpenseCreate
from app.schemas.company import CompanyCreate
from app.schemas.department import DepartmentCreate
from app.schemas.category import CategoryCreate
from app.schemas.user import UserCreate


# Dados de exemplo para despesas
EXPENSE_TEMPLATES = [
    # Mensais
    {"name": "Netflix", "value": 45.90, "currency": Currency.BRL, "periodicity": Periodicity.MONTHLY, "category": "Entretenimento", "payment": PaymentMethod.CREDIT_CARD, "login": "empresa@netflix.com", "password": "senha123"},
    {"name": "Spotify", "value": 16.90, "currency": Currency.BRL, "periodicity": Periodicity.MONTHLY, "category": "Entretenimento", "payment": PaymentMethod.CREDIT_CARD, "login": "empresa@spotify.com", "password": "senha123"},
    {"name": "GitHub", "value": 4.00, "currency": Currency.USD, "periodicity": Periodicity.MONTHLY, "category": "Software", "payment": PaymentMethod.CREDIT_CARD, "login": "empresa@github.com", "password": "senha123"},
    {"name": "AWS", "value": 150.00, "currency": Currency.USD, "periodicity": Periodicity.MONTHLY, "category": "Infraestrutura", "payment": PaymentMethod.CREDIT_CARD, "login": None, "password": None},
    {"name": "Azure", "value": 200.00, "currency": Currency.USD, "periodicity": Periodicity.MONTHLY, "category": "Infraestrutura", "payment": PaymentMethod.CREDIT_CARD, "login": None, "password": None},
    {"name": "Slack", "value": 6.67, "currency": Currency.USD, "periodicity": Periodicity.MONTHLY, "category": "Comunicação", "payment": PaymentMethod.CREDIT_CARD, "login": "empresa@slack.com", "password": "senha123"},
    {"name": "Notion", "value": 8.00, "currency": Currency.USD, "periodicity": Periodicity.MONTHLY, "category": "Software", "payment": PaymentMethod.CREDIT_CARD, "login": "empresa@notion.com", "password": "senha123"},
    {"name": "Zoom", "value": 14.99, "currency": Currency.USD, "periodicity": Periodicity.MONTHLY, "category": "Comunicação", "payment": PaymentMethod.CREDIT_CARD, "login": "empresa@zoom.com", "password": "senha123"},
    
    # Trimestrais
    {"name": "Google Workspace", "value": 18.00, "currency": Currency.USD, "periodicity": Periodicity.QUARTERLY, "category": "Software", "payment": PaymentMethod.CREDIT_CARD, "login": "admin@empresa.com", "password": "senha123"},
    {"name": "Adobe Creative Cloud", "value": 52.99, "currency": Currency.USD, "periodicity": Periodicity.QUARTERLY, "category": "Software", "payment": PaymentMethod.CREDIT_CARD, "login": "design@empresa.com", "password": "senha123"},
    {"name": "Microsoft 365", "value": 12.00, "currency": Currency.USD, "periodicity": Periodicity.QUARTERLY, "category": "Software", "payment": PaymentMethod.CREDIT_CARD, "login": "admin@empresa.com", "password": "senha123"},
    {"name": "HubSpot", "value": 45.00, "currency": Currency.USD, "periodicity": Periodicity.QUARTERLY, "category": "Marketing", "payment": PaymentMethod.CREDIT_CARD, "login": "marketing@empresa.com", "password": "senha123"},
    
    # Semestrais
    {"name": "Certificado SSL", "value": 200.00, "currency": Currency.BRL, "periodicity": Periodicity.SEMIANNUAL, "category": "Infraestrutura", "payment": PaymentMethod.BOLETO, "login": None, "password": None},
    {"name": "Licença de Software", "value": 500.00, "currency": Currency.BRL, "periodicity": Periodicity.SEMIANNUAL, "category": "Software", "payment": PaymentMethod.PIX, "login": None, "password": None},
    
    # Anuais
    {"name": "Domínio .com.br", "value": 40.00, "currency": Currency.BRL, "periodicity": Periodicity.ANNUAL, "category": "Infraestrutura", "payment": PaymentMethod.CREDIT_CARD, "login": None, "password": None},
    {"name": "Seguro Cibernético", "value": 5000.00, "currency": Currency.BRL, "periodicity": Periodicity.ANNUAL, "category": "Segurança", "payment": PaymentMethod.BOLETO, "login": None, "password": None},
]


def ensure_basic_data(db: Session, skip_existing: bool = False) -> dict:
    """
    Garante que existem dados básicos no banco (empresas, departamentos, categorias, usuários).
    Retorna um dicionário com os IDs criados/encontrados.
    """
    result = {
        "company": None,
        "departments": [],
        "categories": [],
        "users": []
    }
    
    # Empresa
    company = get_by_name(db, "Nitro Corp")
    if not company:
        if skip_existing:
            print("⚠️  Empresa não encontrada, mas --skip-existing está ativo. Pulando criação.")
            return result
        print("📦 Criando empresa 'Nitro Corp'...")
        company = create_company(db, CompanyCreate(name="Nitro Corp"))
    else:
        print(f"✓ Empresa '{company.name}' já existe (ID: {company.id})")
    result["company"] = company
    
    # Departamentos
    dept_names = ["Tecnologia", "Marketing", "Financeiro"]
    for dept_name in dept_names:
        dept = get_by_name_and_company(db, dept_name, company.id)
        if not dept:
            if skip_existing:
                continue
            print(f"📦 Criando departamento '{dept_name}'...")
            dept = create_department(db, DepartmentCreate(name=dept_name, company_id=company.id))
        else:
            print(f"✓ Departamento '{dept_name}' já existe (ID: {dept.id})")
        result["departments"].append(dept)
    
    if not result["departments"]:
        print("⚠️  Nenhum departamento disponível. Criando pelo menos um...")
        dept = create_department(db, DepartmentCreate(name="Tecnologia", company_id=company.id))
        result["departments"].append(dept)
    
    # Categorias
    category_names = ["Software", "Infraestrutura", "Marketing", "Comunicação", "Entretenimento", "Segurança"]
    for cat_name in category_names:
        cat = get_by_name(db, cat_name)
        if not cat:
            if skip_existing:
                continue
            print(f"📦 Criando categoria '{cat_name}'...")
            cat = create_category(db, CategoryCreate(name=cat_name))
        else:
            print(f"✓ Categoria '{cat_name}' já existe (ID: {cat.id})")
        result["categories"].append(cat)
    
    if not result["categories"]:
        print("⚠️  Nenhuma categoria disponível. Criando pelo menos uma...")
        cat = create_category(db, CategoryCreate(name="Software"))
        result["categories"].append(cat)
    
    # Usuários
    users_data = [
        {"name": "Admin Finance", "email": "admin@nitro.com", "role": UserRole.FINANCE_ADMIN, "password": "admin123"},
        {"name": "Líder Tech", "email": "leader@nitro.com", "role": UserRole.LEADER, "password": "leader123"},
        {"name": "Líder Teste", "email": "user@nitro.com", "role": UserRole.LEADER, "password": "user123"},
    ]
    
    for user_data in users_data:
        user = get_by_email(db, user_data["email"])
        if not user:
            if skip_existing:
                continue
            print(f"📦 Criando usuário '{user_data['name']}'...")
            dept_ids = [result["departments"][0].id] if result["departments"] else []
            user = create_user(db, UserCreate(
                name=user_data["name"],
                email=user_data["email"],
                password=user_data["password"],
                role=user_data["role"],
                department_ids=dept_ids
            ))
        else:
            print(f"✓ Usuário '{user_data['name']}' já existe (ID: {user.id})")
        result["users"].append(user)
    
    if not result["users"]:
        print("⚠️  Nenhum usuário disponível. Criando pelo menos um admin...")
        user = create_user(db, UserCreate(
            name="Admin Finance",
            email="admin@nitro.com",
            password="admin123",
            role=UserRole.FINANCE_ADMIN,
            department_ids=[result["departments"][0].id] if result["departments"] else []
        ))
        result["users"].append(user)
    
    return result


def convert_to_brl(value: Decimal, currency: Currency) -> tuple[Decimal, Optional[Decimal], Optional[datetime]]:
    """Converte valor para BRL usando serviço de exchange ou fallback."""
    if currency == Currency.BRL:
        return value, None, None
    
    # Tentar buscar cotação
    rate_result = get_usd_to_brl_rate_sync()
    if rate_result:
        rate = rate_result.rate
        rate_date = rate_result.date
    else:
        rate = USD_BRL_FALLBACK_RATE
        rate_date = datetime.now(timezone.utc)
    
    value_brl = value * rate
    return value_brl, rate, rate_date


def create_expense_with_date(
    db: Session,
    template: dict,
    basic_data: dict,
    creation_date: date
) -> Optional[Expense]:
    """Cria uma despesa com created_at definido para uma data específica."""
    try:
        # Selecionar dados aleatórios
        import random
        department = random.choice(basic_data["departments"])
        category = next((c for c in basic_data["categories"] if c.name == template["category"]), basic_data["categories"][0])
        owner = random.choice(basic_data["users"])
        approver = next((u for u in basic_data["users"] if u.role in [UserRole.FINANCE_ADMIN, UserRole.SYSTEM_ADMIN]), basic_data["users"][0])
        
        # Verificar se já existe despesa com mesmo nome
        existing = db.query(Expense).filter(
            Expense.service_name == template["name"],
            Expense.created_at >= datetime(creation_date.year, creation_date.month, 1, tzinfo=timezone.utc),
            Expense.created_at < datetime(creation_date.year, creation_date.month + 1, 1, tzinfo=timezone.utc)
        ).first()
        
        if existing:
            print(f"  ⏭️  Despesa '{template['name']}' já existe para {creation_date.strftime('%Y-%m')}. Pulando...")
            return existing
        
        # Converter para BRL
        value = Decimal(str(template["value"]))
        value_brl, exchange_rate, exchange_rate_date = convert_to_brl(value, template["currency"])
        
        # Criar despesa
        expense_data = ExpenseCreate(
            service_name=template["name"],
            description=f"Assinatura {template['name']} - Criada via seed",
            expense_type=ExpenseType.RECURRING,
            category_id=category.id,
            company_id=basic_data["company"].id,
            department_id=department.id,
            owner_id=owner.id,
            approver_id=approver.id,
            value=value,
            currency=template["currency"],
            periodicity=template["periodicity"],
            payment_method=template["payment"],
            payment_identifier=f"{random.randint(1000, 9999)}",
            login=template.get("login"),
            password=template.get("password"),
        )
        
        expense = create_expense(
            db=db,
            data=expense_data,
            value_brl=value_brl,
            exchange_rate=exchange_rate,
            exchange_rate_date=exchange_rate_date
        )
        
        # Atualizar created_at para a data desejada
        creation_datetime = datetime.combine(creation_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        expense.created_at = creation_datetime
        db.commit()
        db.refresh(expense)
        
        print(f"  ✓ Criada despesa '{template['name']}' (R$ {value_brl:.2f})")
        return expense
        
    except Exception as e:
        print(f"  ✗ Erro ao criar despesa '{template['name']}': {e}")
        db.rollback()
        return None


def create_validations_for_month(
    db: Session,
    expenses: list[Expense],
    validation_month: date
) -> int:
    """Cria validações para o mês especificado baseado na periodicidade das despesas."""
    created_count = 0
    validation_first_day = validation_month.replace(day=1)
    
    for expense in expenses:
        try:
            # Verificar se deve criar validação para este mês
            if not should_create_validation_for_month(expense, validation_first_day):
                continue
            
            # Verificar se já existe validação
            existing = db.query(ExpenseValidation).filter(
                and_(
                    ExpenseValidation.expense_id == expense.id,
                    ExpenseValidation.validation_month == validation_first_day
                )
            ).first()
            
            if existing:
                print(f"  ⏭️  Validação para '{expense.service_name}' já existe para {validation_month.strftime('%Y-%m')}. Pulando...")
                continue
            
            # Criar validação
            validation = ExpenseValidation(
                expense_id=expense.id,
                validator_id=None,
                validation_month=validation_first_day,
                status=ValidationStatus.PENDING,
                is_overdue=False
            )
            db.add(validation)
            created_count += 1
            print(f"  ✓ Criada validação para '{expense.service_name}' ({expense.periodicity.value})")
            
        except Exception as e:
            print(f"  ✗ Erro ao criar validação para '{expense.service_name}': {e}")
            db.rollback()
    
    if created_count > 0:
        db.commit()
    
    return created_count


def main():
    parser = argparse.ArgumentParser(description="Cria despesas de teste e validações")
    parser.add_argument("--month", type=str, default="2026-01", help="Mês de criação das despesas (YYYY-MM)")
    parser.add_argument("--validation-month", type=str, default="2026-02", help="Mês das validações (YYYY-MM)")
    parser.add_argument("--count", type=int, default=15, help="Número de despesas a criar")
    parser.add_argument("--skip-existing", action="store_true", help="Não criar dados básicos se já existirem")
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        creation_month = date.fromisoformat(f"{args.month}-15")
        validation_month = date.fromisoformat(f"{args.validation_month}-01")
    except ValueError as e:
        print(f"❌ Erro ao parsear datas: {e}")
        print("   Use formato YYYY-MM (ex: 2026-01)")
        sys.exit(1)
    
    print("=" * 60)
    print("🌱 Script de Seed de Despesas")
    print("=" * 60)
    print(f"📅 Mês de criação: {creation_month.strftime('%Y-%m')}")
    print(f"📅 Mês de validação: {validation_month.strftime('%Y-%m')}")
    print(f"📊 Número de despesas: {args.count}")
    print("=" * 60)
    print()
    
    db: Session = SessionLocal()
    try:
        # 1. Garantir dados básicos
        print("📋 Verificando/Criando dados básicos...")
        basic_data = ensure_basic_data(db, skip_existing=args.skip_existing)
        print()
        
        if not basic_data["company"] or not basic_data["departments"] or not basic_data["categories"] or not basic_data["users"]:
            print("❌ Dados básicos insuficientes. Execute sem --skip-existing ou crie manualmente.")
            sys.exit(1)
        
        # 2. Criar despesas
        print(f"💰 Criando {args.count} despesas...")
        created_expenses = []
        templates_to_use = EXPENSE_TEMPLATES[:args.count] if args.count <= len(EXPENSE_TEMPLATES) else EXPENSE_TEMPLATES * ((args.count // len(EXPENSE_TEMPLATES)) + 1)
        
        for i, template in enumerate(templates_to_use[:args.count], 1):
            print(f"[{i}/{args.count}] {template['name']}...")
            expense = create_expense_with_date(db, template, basic_data, creation_month)
            if expense:
                created_expenses.append(expense)
        print()
        
        # 3. Criar validações
        print(f"✅ Criando validações para {validation_month.strftime('%Y-%m')}...")
        validation_count = create_validations_for_month(db, created_expenses, validation_month)
        print()
        
        # Resumo
        print("=" * 60)
        print("📊 Resumo")
        print("=" * 60)
        print(f"✓ Despesas criadas: {len(created_expenses)}")
        print(f"✓ Validações criadas: {validation_count}")
        print()
        print("🎉 Seed concluído com sucesso!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
