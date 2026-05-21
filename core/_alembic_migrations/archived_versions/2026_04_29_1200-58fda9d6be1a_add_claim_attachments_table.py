"""Add claim attachments table

Revision ID: 58fda9d6be1a
Revises: 9c74e6e1c8af
Create Date: 2026-04-29 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from _alembic_migrations.tenant import for_each_project_schema
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58fda9d6be1a"
down_revision: str | None = "9c74e6e1c8af"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


@for_each_project_schema
def upgrade(schema: str) -> None:
    op.create_table(
        "claim_attachments",
        sa.Column(
            "claim_attachment_id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("claim_update_id", sa.Integer(), nullable=True),
        sa.Column("s3_key", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            [f"{schema}.claims.claim_id"],
            name=op.f("claim_attachments_claim_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["claim_update_id"],
            [f"{schema}.claim_updates.claim_update_id"],
            name=op.f("claim_attachments_claim_update_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("claim_attachment_id"),
        sa.UniqueConstraint(
            "claim_id",
            "filename",
            name=op.f("uq_claim_attachments_claim_filename"),
        ),
        sa.UniqueConstraint(
            "s3_key",
            name=op.f("uq_claim_attachments_s3_key"),
        ),
        schema=schema,
    )
    op.create_index(
        op.f("ix_claim_attachments_claim_update_id"),
        "claim_attachments",
        ["claim_update_id"],
        unique=False,
        schema=schema,
    )


@for_each_project_schema
def downgrade(schema: str) -> None:
    op.drop_index(
        op.f("ix_claim_attachments_claim_update_id"),
        table_name="claim_attachments",
        schema=schema,
    )
    op.drop_table("claim_attachments", schema=schema)
