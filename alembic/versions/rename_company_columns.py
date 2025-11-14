"""Rename company_url to username and company_name to title in linkedin_company_members

Revision ID: rename_company_columns
Revises: rename_linkedin_url
Create Date: 2025-11-14 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'rename_company_columns'
down_revision: Union[str, None] = 'rename_linkedin_url'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old unique constraint
    op.drop_constraint('linkedin_company_members_linkedin_profile_id_company_url_key', 'linkedin_company_members', type_='unique')

    # Rename columns
    op.alter_column('linkedin_company_members', 'company_url', new_column_name='username')
    op.alter_column('linkedin_company_members', 'company_name', new_column_name='title')

    # Create new unique constraint with the renamed columns
    op.create_unique_constraint(
        'linkedin_company_members_linkedin_profile_id_username_key',
        'linkedin_company_members',
        ['linkedin_profile_id', 'username']
    )


def downgrade() -> None:
    # Drop the new unique constraint
    op.drop_constraint('linkedin_company_members_linkedin_profile_id_username_key', 'linkedin_company_members', type_='unique')

    # Rename columns back
    op.alter_column('linkedin_company_members', 'username', new_column_name='company_url')
    op.alter_column('linkedin_company_members', 'title', new_column_name='company_name')

    # Create old unique constraint
    op.create_unique_constraint(
        'linkedin_company_members_linkedin_profile_id_company_url_key',
        'linkedin_company_members',
        ['linkedin_profile_id', 'company_url']
    )