"""create user_companies table for leader/finance_admin company scope

Revision ID: g9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-02-12 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.config import settings

revision: str = 'g9b0c1d2e3f4'
down_revision: Union[str, Sequence[str], None] = 'f8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = settings.DATABASE_SCHEMA


def upgrade() -> None:
    op.create_table(
        'user_companies',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], [f'{SCHEMA}.users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], [f'{SCHEMA}.companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'company_id'),
        schema=SCHEMA
    )
    op.create_index('ix_user_companies_company_id', 'user_companies', ['company_id'], unique=False, schema=SCHEMA)


def downgrade() -> None:
    op.drop_index('ix_user_companies_company_id', table_name='user_companies', schema=SCHEMA)
    op.drop_table('user_companies', schema=SCHEMA)
