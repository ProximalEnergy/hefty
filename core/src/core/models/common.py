"""SQLAlchemy models defining the database schema."""

from typing import TypeVar

from sqlalchemy import Enum
from sqlalchemy.types import UserDefinedType

from core import enumerations
from core.database import Base

T = TypeVar("T")


class LTree(UserDefinedType):
    """
    Minimal custom type telling SQLAlchemy to use 'LTREE'
    as the column type in PostgreSQL.
    This is enough for Alembic to autogenerate `LTREE` columns for new tables/columns.
    """

    def get_col_spec(self, **kw) -> str:  # noqa
        # The exact column type specification used in CREATE TABLE
        """Return the SQL column type spec for LTREE.

        Args:
            **kw: Dialect-specific keyword arguments (unused).
        """
        return "LTREE"


# --- Postgres Enum Types ---
# We attach these to metadata so they aren't tied to just one table
notification_severity_enum = Enum(
    enumerations.NotificationSeverity,
    name="notification_severity",
    schema="admin",
    metadata=Base.metadata,
)

notification_channel_enum = Enum(
    enumerations.NotificationChannelEnum,
    name="notification_channel",
    schema="admin",
    metadata=Base.metadata,
)

notification_state_enum = Enum(
    enumerations.NotificationStateEnum,
    name="notification_state",
    schema="admin",
    metadata=Base.metadata,
)

claim_submission_channel_enum = Enum(
    enumerations.ClaimSubmissionChannel,
    values_callable=lambda e: [m.value for m in e],
    name="claimsubmissionchannel",
    schema="operational",
    metadata=Base.metadata,
)

claim_status_enum = Enum(
    enumerations.ClaimStatus,
    values_callable=lambda e: [m.value for m in e],
    name="claimstatus",
    schema="operational",
    metadata=Base.metadata,
)

claim_update_type_enum = Enum(
    enumerations.ClaimUpdateType,
    values_callable=lambda e: [m.value for m in e],
    name="claimupdatetype",
    schema="operational",
    metadata=Base.metadata,
)
