"""fix issues fkey

Revision ID: fd675e1f21d9
Revises: 09364c6d5d8f
Create Date: 2026-04-22 17:11:34.990061+00:00

"""

from _alembic_migrations.tenant import for_each_project_schema
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fd675e1f21d9"
down_revision: str | None = "09364c6d5d8f"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


@for_each_project_schema
def upgrade(schema: str) -> None:
    op.drop_constraint(
        op.f("issues_device_id_fkey"),
        "issues",
        schema=schema,
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("issues_device_id_fkey"),
        "issues",
        "devices",
        ["device_id"],
        ["device_id"],
        source_schema=schema,
        referent_schema=schema,
    )


@for_each_project_schema
def downgrade(schema: str) -> None:
    op.drop_constraint(
        op.f("issues_device_id_fkey"),
        "issues",
        schema=schema,
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("issues_device_id_fkey"),
        "issues",
        "devices",
        ["device_id"],
        ["device_id"],
        source_schema=schema,
        referent_schema="project_default",
    )
