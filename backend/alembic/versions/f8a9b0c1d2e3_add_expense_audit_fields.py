"""add created_by_id, cancelled_at, cancelled_by_id to expenses

Revision ID: f8a9b0c1d2e3
Revises: e6f7a8b9c0d1
Create Date: 2026-02-12 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f8a9b0c1d2e3'
down_revision: Union[str, Sequence[str], None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('expenses', sa.Column('created_by_id', sa.UUID(), nullable=True))
    op.add_column('expenses', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('expenses', sa.Column('cancelled_by_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_expenses_created_by_id_users',
        'expenses', 'users',
        ['created_by_id'], ['id'],
    )
    op.create_foreign_key(
        'fk_expenses_cancelled_by_id_users',
        'expenses', 'users',
        ['cancelled_by_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_expenses_cancelled_by_id_users', 'expenses', type_='foreignkey')
    op.drop_constraint('fk_expenses_created_by_id_users', 'expenses', type_='foreignkey')
    op.drop_column('expenses', 'cancelled_by_id')
    op.drop_column('expenses', 'cancelled_at')
    op.drop_column('expenses', 'created_by_id')
