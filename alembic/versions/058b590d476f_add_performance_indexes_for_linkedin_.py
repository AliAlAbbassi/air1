"""add_performance_indexes_for_linkedin_profile

Revision ID: 058b590d476f
Revises: rename_company_columns
Create Date: 2025-11-15 21:55:07.289214

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '058b590d476f'
down_revision: Union[str, Sequence[str], None] = 'rename_company_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for LinkedIn profile queries."""
    # Enable pg_trgm extension for trigram similarity searches
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Foreign key index for join performance
    op.create_index(
        'idx_linkedin_profile_lead_id',
        'linkedin_profile',
        ['lead_id']
    )

    # Trigram GIN index for fast text search on headline
    op.execute("""
        CREATE INDEX idx_linkedin_profile_headline_gin
        ON linkedin_profile
        USING gin(headline gin_trgm_ops)
    """)

    # Additional index for username lookups (already unique, but for performance)
    op.create_index(
        'idx_linkedin_profile_username_btree',
        'linkedin_profile',
        ['username']
    )


def downgrade() -> None:
    """Remove performance indexes for LinkedIn profile queries."""
    # Drop indexes in reverse order
    op.drop_index('idx_linkedin_profile_username_btree', table_name='linkedin_profile')
    op.execute("DROP INDEX IF EXISTS idx_linkedin_profile_headline_gin")
    op.drop_index('idx_linkedin_profile_lead_id', table_name='linkedin_profile')

    # Note: We don't drop the pg_trgm extension as other parts of the system might use it
