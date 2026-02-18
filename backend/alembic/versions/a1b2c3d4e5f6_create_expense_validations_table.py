"""create expense_validations table

Revision ID: a1b2c3d4e5f6
Revises: 3828ab3e1869
Create Date: 2026-01-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '3828ab3e1869'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = settings.DATABASE_SCHEMA


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    
    # Criar enum ValidationStatus (se não existir)
    conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE validationstatus AS ENUM ('pending', 'approved', 'rejected');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Verificar se tabela já existe
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = '{SCHEMA}' 
            AND table_name = 'expense_validations'
        );
    """))
    table_exists = result.scalar()
    
    if not table_exists:
        # Criar tabela usando SQL direto para evitar problema com Enum do SQLAlchemy
        conn.execute(text(f"""
            CREATE TABLE {SCHEMA}.expense_validations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                expense_id UUID NOT NULL REFERENCES {SCHEMA}.expenses(id),
                validator_id UUID NOT NULL REFERENCES {SCHEMA}.users(id),
                validation_month DATE NOT NULL,
                status validationstatus NOT NULL DEFAULT 'pending',
                validated_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE,
                CONSTRAINT uq_expense_validation_month UNIQUE (expense_id, validation_month)
            );
        """))
        
        # Criar índices
        conn.execute(text(f"""
            CREATE INDEX idx_expense_validation_expense_month 
            ON {SCHEMA}.expense_validations (expense_id, validation_month);
        """))
        
        conn.execute(text(f"""
            CREATE INDEX idx_expense_validation_validator_status 
            ON {SCHEMA}.expense_validations (validator_id, status);
        """))
        
        conn.commit()


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_expense_validation_validator_status', table_name='expense_validations', schema=SCHEMA)
    op.drop_index('idx_expense_validation_expense_month', table_name='expense_validations', schema=SCHEMA)
    op.drop_table('expense_validations', schema=SCHEMA)
    op.execute("DROP TYPE validationstatus")
