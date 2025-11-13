"""Initial schema

Revision ID: 4a192acc912c
Revises: 
Create Date: 2025-11-11 22:44:55.208963

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a192acc912c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from pathlib import Path

    # Get all SQL model files
    base_dir = Path(__file__).parent.parent.parent
    models_dir = base_dir / "air1" / "db" / "models"

    # Execute SQL files in order (lead first, then linkedin which depends on it)
    sql_files = sorted(models_dir.glob("*.sql"))

    for sql_file in sql_files:
        with open(sql_file, "r") as f:
            sql = f.read()
            # Skip commented drop statements
            sql_lines = [line for line in sql.splitlines()
                        if not line.strip().startswith("-- drop")]
            op.execute("\n".join(sql_lines))


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order due to foreign key constraints
    op.execute("DROP TABLE IF EXISTS linkedin_company_members CASCADE")
    op.execute("DROP TABLE IF EXISTS linkedin_profile CASCADE")
    op.execute("DROP TABLE IF EXISTS lead CASCADE")
    op.execute("DROP FUNCTION IF EXISTS update_updated_on_column() CASCADE")
