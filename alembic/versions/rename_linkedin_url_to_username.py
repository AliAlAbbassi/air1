"""Rename linkedin_url to linkedin_username

Revision ID: rename_linkedin_url
Revises: 39ec6c817588
Create Date: 2025-11-14 20:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'rename_linkedin_url'
down_revision: Union[str, None] = '39ec6c817588'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename the column
    op.alter_column('linkedin_profile', 'linkedin_url', new_column_name='username')

    # Drop the old unique constraint
    op.drop_constraint('linkedin_profile_linkedin_url_key', 'linkedin_profile', type_='unique')

    # Create new unique constraint
    op.create_unique_constraint('linkedin_profile_username_key', 'linkedin_profile', ['username'])


def downgrade() -> None:
    # Drop the new unique constraint
    op.drop_constraint('linkedin_profile_username_key', 'linkedin_profile', type_='unique')

    # Create old unique constraint
    op.create_unique_constraint('linkedin_profile_linkedin_url_key', 'linkedin_profile', ['linkedin_url'])

    # Rename the column back
    op.alter_column('linkedin_profile', 'username', new_column_name='linkedin_url')