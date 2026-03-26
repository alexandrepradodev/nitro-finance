"""add review_status to expenses

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-03-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j2k3l4m5n6o7'
down_revision: Union[str, Sequence[str], None] = 'i1j2k3l4m5n6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    review_status_enum = sa.Enum('normal', 'review', name='reviewstatus')
    review_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'expenses',
        sa.Column(
            'review_status',
            review_status_enum,
            nullable=False,
            server_default='normal',
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('expenses', 'review_status')
    review_status_enum = sa.Enum('normal', 'review', name='reviewstatus')
    review_status_enum.drop(op.get_bind(), checkfirst=True)
