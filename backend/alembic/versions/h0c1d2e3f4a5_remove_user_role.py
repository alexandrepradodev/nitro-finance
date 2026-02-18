"""remove user role: migrate existing users to leader

Revision ID: h0c1d2e3f4a5
Revises: g9b0c1d2e3f4
Create Date: 2026-02-12 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

from app.core.config import settings

revision: str = 'h0c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = 'g9b0c1d2e3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = settings.DATABASE_SCHEMA


def upgrade() -> None:
    # Data migration: users with role 'user' or 'USER' become 'leader' / 'LEADER'
    # Enum was created with uppercase names in create_initial_tables
    op.execute(
        f"UPDATE {SCHEMA}.users SET role = 'LEADER' WHERE role::text IN ('USER', 'user')"
    )


def downgrade() -> None:
    # Revert: leader back to user only where we cannot distinguish; leave as-is (no safe revert)
    pass
