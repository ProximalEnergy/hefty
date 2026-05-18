"""add poa sensor issue category

Revision ID: a9b8c7d6e5f4
Revises: 93d2244c759a
Create Date: 2026-05-18 17:51:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: str | None = "93d2244c759a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        text(
            """
            INSERT INTO operational.issue_categories
                (issue_category_id, name_long)
            VALUES
                (1, 'POA Sensor Out of Position')
            ON CONFLICT (issue_category_id) DO UPDATE
            SET name_long = EXCLUDED.name_long
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            DELETE FROM operational.issue_categories
            WHERE issue_category_id = 1
                AND name_long = 'POA Sensor Out of Position'
            """
        )
    )
