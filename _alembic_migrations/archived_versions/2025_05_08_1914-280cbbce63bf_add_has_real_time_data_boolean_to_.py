"""add has_real_time_data boolean to project table

Revision ID: 280cbbce63bf
Revises: b0b2ec533da4
Create Date: 2025-05-08 19:14:50.816118+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "280cbbce63bf"
down_revision: str | None = "b0b2ec533da4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "has_real_time_data",
            sa.Boolean(),
            server_default="FALSE",
            nullable=False,
        ),
        schema="operational",
    )


def downgrade() -> None:
    op.drop_column("projects", "has_real_time_data", schema="operational")
