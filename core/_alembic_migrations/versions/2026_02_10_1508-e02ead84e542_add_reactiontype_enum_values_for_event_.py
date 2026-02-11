"""Add ReactionType enum values for event chat

Revision ID: e02ead84e542
Revises: 530731d657ec
Create Date: 2026-02-10 03:08:34.788974+00:00

"""

import logging
from collections.abc import Sequence

from _alembic_migrations.tenant import for_each_project_schema
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "e02ead84e542"
down_revision: str | None = "d2f3bbc73e64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REACTION_VALUES = (
    "thumbs_up",
    "thumbs_down",
    "fire",
    "eyes",
    "question_mark",
    "heart",
    "laughing",
    "surprised",
    "sad",
    "angry",
    "party",
    "check",
    "clap",
    "hundred",
    "rocket",
    "lightbulb",
    "star",
    "target",
    "pray",
)


@for_each_project_schema
def upgrade(schema: str) -> None:
    logger = logging.getLogger("alembic.runtime.migration")
    safe_schema = schema.replace('"', '""')
    connection = op.get_bind()

    # 1. Fetch existing enum values for this schema (if they exist)
    get_values_sql = text(
        """
        SELECT e.enumlabel
        FROM pg_enum e
        JOIN pg_type t ON e.enumtypid = t.oid
        JOIN pg_namespace n ON t.typnamespace = n.oid
        WHERE n.nspname = :schema AND t.typname = 'reactiontype'
        ORDER BY e.enumsortorder;
        """
    )

    existing_rows = connection.execute(get_values_sql, {"schema": schema}).fetchall()
    existing_values = {row[0] for row in existing_rows}

    # 2. Case: Type does not exist at all -> CREATE
    if not existing_rows:
        logger.info(
            "Creating 'reactiontype' from scratch in schema: %s",
            schema,
        )
        values_str = ", ".join([f"'{v}'" for v in REACTION_VALUES])
        op.execute(
            text(f'CREATE TYPE "{safe_schema}".reactiontype AS ENUM ({values_str})')
        )
        return

    # 3. Case: Type exists -> ALTER to add missing values
    logger.info("Syncing 'reactiontype' values in schema: %s", schema)
    for value in REACTION_VALUES:
        if value not in existing_values:
            # "IF NOT EXISTS" is a safety net, though our check handles it.
            sql = (
                f'ALTER TYPE "{safe_schema}".reactiontype '
                f"ADD VALUE IF NOT EXISTS '{value}'"
            )
            op.execute(text(sql))


@for_each_project_schema
def downgrade(schema: str) -> None:
    # PostgreSQL does not support removing enum values; leave new values in place.
    pass
