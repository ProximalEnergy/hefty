"""Add autoincrement behavior to project_id_int

Revision ID: 40f280a6dc95
Revises: 135627950305
Create Date: 2026-01-07 19:16:12.278716+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "40f280a6dc95"
down_revision: str | None = "135627950305"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Remember to remove any operations unrelated to your migration!
# Are you making changes to the project schemas?
#   If so, pass the `schema` arg to all operations (`op` functions)
#   If not, remove the `for_each_project_schema` decorator and
#   `schema` arg in `upgrade` and `downgrade` functions


def upgrade() -> None:
    # Create sequence if it doesn't exist
    op.execute(
        text(
            """
            CREATE SEQUENCE IF NOT EXISTS operational.projects_project_id_int_seq
            AS SMALLINT
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1
            """
        )
    )

    # Set default to use the sequence
    op.execute(
        text(
            """
            ALTER TABLE operational.projects
            ALTER COLUMN project_id_int
            SET DEFAULT nextval('operational.projects_project_id_int_seq')
            """
        )
    )

    # Make column non-nullable
    op.alter_column(
        "projects",
        "project_id_int",
        existing_type=sa.SMALLINT(),
        nullable=False,
        schema="operational",
    )


def downgrade() -> None:
    # Make column nullable
    op.alter_column(
        "projects",
        "project_id_int",
        existing_type=sa.SMALLINT(),
        nullable=True,
        schema="operational",
    )

    # Remove default
    op.execute(
        text(
            """
            ALTER TABLE operational.projects
            ALTER COLUMN project_id_int
            DROP DEFAULT
            """
        )
    )

    # Drop sequence
    op.execute(text("DROP SEQUENCE IF EXISTS operational.projects_project_id_int_seq"))
