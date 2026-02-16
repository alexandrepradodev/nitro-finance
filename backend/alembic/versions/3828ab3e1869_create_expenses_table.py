"""create expenses table

Revision ID: 3828ab3e1869
Revises: 715f5542bda3
Create Date: 2026-01-29 07:45:10.769377

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3828ab3e1869'
down_revision: Union[str, Sequence[str], None] = '715f5542bda3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Migration duplicada da 715f5542bda3 - todas as operações já foram
    # executadas pela migration anterior. Mantida apenas para preservar
    # a cadeia de revisões do Alembic.
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
