"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

from _alembic_migrations.tenant import for_each_project_schema

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}

# Remember to remove any operations unrelated to your migration!
# Are you making changes to the project schemas?
#   If so, pass the `schema` arg to all operations (`op` functions)
#   If not, remove the `for_each_project_schema` decorator and `schema` arg in `upgrade` and `downgrade` functions 


@for_each_project_schema
def upgrade(schema: str) -> None:
    ${upgrades if upgrades else "pass"}


@for_each_project_schema
def downgrade(schema: str) -> None:
    ${downgrades if downgrades else "pass"}
