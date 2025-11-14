"""Make email optional in lead table

Revision ID: 39ec6c817588
Revises: 4a192acc912c
Create Date: 2025-11-13 19:36:59.028963

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39ec6c817588'
down_revision: Union[str, Sequence[str], None] = '4a192acc912c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('lead', 'email',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('lead', 'email',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=False)
