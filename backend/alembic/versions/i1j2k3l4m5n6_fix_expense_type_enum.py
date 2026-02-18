"""fix expense enums values to lowercase

Revision ID: i1j2k3l4m5n6
Revises: h0c1d2e3f4a5
Create Date: 2026-02-16 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from app.core.config import settings

revision: str = 'i1j2k3l4m5n6'
down_revision: Union[str, Sequence[str], None] = 'h0c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = settings.DATABASE_SCHEMA


def upgrade() -> None:
    """Altera os valores dos enums de maiúsculas para minúsculas."""
    conn = op.get_bind()
    
    # 1. Corrigir expensetype
    conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE expensetype_new AS ENUM ('recurring', 'one_time');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(text(f"""
        ALTER TABLE {SCHEMA}.expenses 
        ALTER COLUMN expense_type TYPE expensetype_new 
        USING CASE 
            WHEN expense_type::text = 'RECURRING' THEN 'recurring'::expensetype_new
            WHEN expense_type::text = 'ONE_TIME' THEN 'one_time'::expensetype_new
            ELSE expense_type::text::expensetype_new
        END;
    """))
    
    conn.execute(text("DROP TYPE IF EXISTS expensetype CASCADE;"))
    conn.execute(text("ALTER TYPE expensetype_new RENAME TO expensetype;"))
    
    # 2. Corrigir periodicity
    conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE periodicity_new AS ENUM ('monthly', 'quarterly', 'semiannual', 'annual');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(text(f"""
        ALTER TABLE {SCHEMA}.expenses 
        ALTER COLUMN periodicity TYPE periodicity_new 
        USING CASE 
            WHEN periodicity::text = 'MONTHLY' THEN 'monthly'::periodicity_new
            WHEN periodicity::text = 'QUARTERLY' THEN 'quarterly'::periodicity_new
            WHEN periodicity::text = 'SEMIANNUAL' THEN 'semiannual'::periodicity_new
            WHEN periodicity::text = 'ANNUAL' THEN 'annual'::periodicity_new
            ELSE periodicity::text::periodicity_new
        END;
    """))
    
    conn.execute(text("DROP TYPE IF EXISTS periodicity CASCADE;"))
    conn.execute(text("ALTER TYPE periodicity_new RENAME TO periodicity;"))
    
    # 3. Corrigir paymentmethod
    conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE paymentmethod_new AS ENUM ('credit_card', 'debit_card', 'boleto', 'pix', 'transfer');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(text(f"""
        ALTER TABLE {SCHEMA}.expenses 
        ALTER COLUMN payment_method TYPE paymentmethod_new 
        USING CASE 
            WHEN payment_method::text = 'CREDIT_CARD' THEN 'credit_card'::paymentmethod_new
            WHEN payment_method::text = 'DEBIT_CARD' THEN 'debit_card'::paymentmethod_new
            WHEN payment_method::text = 'BOLETO' THEN 'boleto'::paymentmethod_new
            WHEN payment_method::text = 'PIX' THEN 'pix'::paymentmethod_new
            WHEN payment_method::text = 'TRANSFER' THEN 'transfer'::paymentmethod_new
            ELSE payment_method::text::paymentmethod_new
        END;
    """))
    
    conn.execute(text("DROP TYPE IF EXISTS paymentmethod CASCADE;"))
    conn.execute(text("ALTER TYPE paymentmethod_new RENAME TO paymentmethod;"))
    
    # 4. Corrigir expensestatus
    conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE expensestatus_new AS ENUM ('draft', 'in_review', 'active', 'cancellation_requested', 'cancelled', 'suspended', 'migrated');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(text(f"""
        ALTER TABLE {SCHEMA}.expenses 
        ALTER COLUMN status TYPE expensestatus_new 
        USING CASE 
            WHEN status::text = 'DRAFT' THEN 'draft'::expensestatus_new
            WHEN status::text = 'IN_REVIEW' THEN 'in_review'::expensestatus_new
            WHEN status::text = 'ACTIVE' THEN 'active'::expensestatus_new
            WHEN status::text = 'CANCELLATION_REQUESTED' THEN 'cancellation_requested'::expensestatus_new
            WHEN status::text = 'CANCELLED' THEN 'cancelled'::expensestatus_new
            WHEN status::text = 'SUSPENDED' THEN 'suspended'::expensestatus_new
            WHEN status::text = 'MIGRATED' THEN 'migrated'::expensestatus_new
            ELSE status::text::expensestatus_new
        END;
    """))
    
    conn.execute(text("DROP TYPE IF EXISTS expensestatus CASCADE;"))
    conn.execute(text("ALTER TYPE expensestatus_new RENAME TO expensestatus;"))


def downgrade() -> None:
    """Reverte os valores dos enums para maiúsculas."""
    conn = op.get_bind()
    
    # 1. Reverter expensetype
    conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE expensetype_old AS ENUM ('RECURRING', 'ONE_TIME');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(text(f"""
        ALTER TABLE {SCHEMA}.expenses 
        ALTER COLUMN expense_type TYPE expensetype_old 
        USING CASE 
            WHEN expense_type::text = 'recurring' THEN 'RECURRING'::expensetype_old
            WHEN expense_type::text = 'one_time' THEN 'ONE_TIME'::expensetype_old
            ELSE expense_type::text::expensetype_old
        END;
    """))
    
    conn.execute(text("DROP TYPE IF EXISTS expensetype CASCADE;"))
    conn.execute(text("ALTER TYPE expensetype_old RENAME TO expensetype;"))
    
    # 2. Reverter periodicity
    conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE periodicity_old AS ENUM ('MONTHLY', 'QUARTERLY', 'SEMIANNUAL', 'ANNUAL');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(text(f"""
        ALTER TABLE {SCHEMA}.expenses 
        ALTER COLUMN periodicity TYPE periodicity_old 
        USING CASE 
            WHEN periodicity::text = 'monthly' THEN 'MONTHLY'::periodicity_old
            WHEN periodicity::text = 'quarterly' THEN 'QUARTERLY'::periodicity_old
            WHEN periodicity::text = 'semiannual' THEN 'SEMIANNUAL'::periodicity_old
            WHEN periodicity::text = 'annual' THEN 'ANNUAL'::periodicity_old
            ELSE periodicity::text::periodicity_old
        END;
    """))
    
    conn.execute(text("DROP TYPE IF EXISTS periodicity CASCADE;"))
    conn.execute(text("ALTER TYPE periodicity_old RENAME TO periodicity;"))
    
    # 3. Reverter paymentmethod
    conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE paymentmethod_old AS ENUM ('CREDIT_CARD', 'DEBIT_CARD', 'BOLETO', 'PIX', 'TRANSFER');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(text(f"""
        ALTER TABLE {SCHEMA}.expenses 
        ALTER COLUMN payment_method TYPE paymentmethod_old 
        USING CASE 
            WHEN payment_method::text = 'credit_card' THEN 'CREDIT_CARD'::paymentmethod_old
            WHEN payment_method::text = 'debit_card' THEN 'DEBIT_CARD'::paymentmethod_old
            WHEN payment_method::text = 'boleto' THEN 'BOLETO'::paymentmethod_old
            WHEN payment_method::text = 'pix' THEN 'PIX'::paymentmethod_old
            WHEN payment_method::text = 'transfer' THEN 'TRANSFER'::paymentmethod_old
            ELSE payment_method::text::paymentmethod_old
        END;
    """))
    
    conn.execute(text("DROP TYPE IF EXISTS paymentmethod CASCADE;"))
    conn.execute(text("ALTER TYPE paymentmethod_old RENAME TO paymentmethod;"))
    
    # 4. Reverter expensestatus
    conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE expensestatus_old AS ENUM ('DRAFT', 'IN_REVIEW', 'ACTIVE', 'CANCELLATION_REQUESTED', 'CANCELLED', 'SUSPENDED', 'MIGRATED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(text(f"""
        ALTER TABLE {SCHEMA}.expenses 
        ALTER COLUMN status TYPE expensestatus_old 
        USING CASE 
            WHEN status::text = 'draft' THEN 'DRAFT'::expensestatus_old
            WHEN status::text = 'in_review' THEN 'IN_REVIEW'::expensestatus_old
            WHEN status::text = 'active' THEN 'ACTIVE'::expensestatus_old
            WHEN status::text = 'cancellation_requested' THEN 'CANCELLATION_REQUESTED'::expensestatus_old
            WHEN status::text = 'cancelled' THEN 'CANCELLED'::expensestatus_old
            WHEN status::text = 'suspended' THEN 'SUSPENDED'::expensestatus_old
            WHEN status::text = 'migrated' THEN 'MIGRATED'::expensestatus_old
            ELSE status::text::expensestatus_old
        END;
    """))
    
    conn.execute(text("DROP TYPE IF EXISTS expensestatus CASCADE;"))
    conn.execute(text("ALTER TYPE expensestatus_old RENAME TO expensestatus;"))
