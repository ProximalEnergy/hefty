"""Add ReactionType enum values for event chat

Revision ID: e02ead84e542
Revises: 530731d657ec
Create Date: 2026-02-10 03:08:34.788974+00:00

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "e02ead84e542"
down_revision: str | None = "d2f3bbc73e64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_REACTION_VALUES = (
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


def upgrade(schema: str) -> None:
    # Escape double quotes in schema name per PostgreSQL identifier quoting
    safe_schema = schema.replace('"', '""')
    for value in NEW_REACTION_VALUES:
        sql = (
            f'ALTER TYPE "{safe_schema}".reactiontype '
            f"ADD VALUE IF NOT EXISTS '{value}'"
        )
        op.execute(text(sql))


def downgrade(schema: str) -> None:
    # PostgreSQL does not support removing enum values; leave new values in place.
    pass
