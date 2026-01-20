"""create initial tables

Revision ID: f7cabbc606c8
Revises: 
Create Date: 2026-01-20 10:28:52.660140

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7cabbc606c8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = 'public'


def upgrade() -> None:
    """Upgrade schema."""
    
    # Criar schema se não existir
    op.execute(f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}')
    
    op.create_table('categories',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        schema=SCHEMA
    )
    
    op.create_table('companies',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        schema=SCHEMA
    )
    
    op.create_table('users',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('FINANCE_ADMIN', 'SYSTEM_ADMIN', 'LEADER', 'USER', name='userrole', schema=SCHEMA), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True, schema=SCHEMA)
    
    op.create_table('departments',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], [f'{SCHEMA}.companies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA
    )
    
    op.create_table('user_departments',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('department_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], [f'{SCHEMA}.departments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], [f'{SCHEMA}.users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'department_id'),
        schema=SCHEMA
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_departments', schema=SCHEMA)
    op.drop_table('departments', schema=SCHEMA)
    op.drop_index(op.f('ix_users_email'), table_name='users', schema=SCHEMA)
    op.drop_table('users', schema=SCHEMA)
    op.drop_table('companies', schema=SCHEMA)
    op.drop_table('categories', schema=SCHEMA)