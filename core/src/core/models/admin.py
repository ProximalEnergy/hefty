"""SQLAlchemy admin schema models."""

import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy import SmallInteger, func
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core import enumerations
from core.database import Base

from .common import (
    notification_channel_enum,
    notification_severity_enum,
    notification_state_enum,
)


##### START ADMIN SCHEMA #####
# NOTE: Every model in the admin schema must specify
#  `__table_args__ = {"schema": "admin"}`
class Company(Base):
    __tablename__ = "companies"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text(
            "gen_random_uuid()",
        ),  # Have database generate a UUID for the company_id
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]

    teams = relationship("Team", back_populates="company")

    __table_args__ = {"schema": "admin"}


class CompanyPermission(Base):
    __tablename__ = "company_permissions"

    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
        primary_key=True,
    )
    permission_id: Mapped[int] = mapped_column(
        sa.ForeignKey("admin.permissions.permission_id"),
        primary_key=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
        primary_key=True,
    )

    __table_args__ = {"schema": "admin"}


class CompanySecrets(Base):
    __tablename__ = "company_secrets"
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
        primary_key=True,
    )
    dtn_secret_id: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=True,
    )

    __table_args__ = {"schema": "admin"}


class CompanyProject(Base):
    __tablename__ = "company_projects"

    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
        primary_key=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
        primary_key=True,
    )
    vector_store_id: Mapped[str]
    data_access_start: Mapped[datetime.date | None]

    __table_args__ = {"schema": "admin"}


class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
        index=True,
    )
    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    subject: Mapped[str]
    url: Mapped[str | None]
    comment: Mapped[str]
    screenshot: Mapped[bytes | None] = mapped_column(BYTEA)
    screenshot_filename: Mapped[str | None]
    screenshot_mimetype: Mapped[str | None]
    reviewed: Mapped[bool] = mapped_column(server_default="false")
    completed: Mapped[bool] = mapped_column(server_default="false")

    user = relationship("User")

    __table_args__ = {"schema": "admin"}


class Permission(Base):
    __tablename__ = "permissions"

    permission_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str] = mapped_column()

    __table_args__ = {"schema": "admin"}


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    user_type_id: Mapped[enumerations.UserTypeEnum] = mapped_column(
        sa.SmallInteger,
        sa.ForeignKey("admin.user_types.user_type_id"),
        server_default=str(enumerations.UserTypeEnum.USER),  # Default to "user" level
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
    )
    name_long: Mapped[str | None]
    api_key: Mapped[str | None] = mapped_column(unique=True)

    team_memberships = relationship("TeamMember", back_populates="user")

    __table_args__ = {"schema": "admin"}


class UserPermission(Base):
    __tablename__ = "user_permissions"

    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
        primary_key=True,
    )
    permission_id: Mapped[int] = mapped_column(
        sa.ForeignKey("admin.permissions.permission_id"),
        primary_key=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
        primary_key=True,
    )

    __table_args__ = {"schema": "admin"}


class UserProject(Base):
    __tablename__ = "user_projects"

    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
        primary_key=True,
    )
    operational_project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
        primary_key=True,
    )
    is_favorited: Mapped[bool] = mapped_column(server_default="false")

    __table_args__ = {"schema": "admin"}


class UserKPITypes(Base):
    __tablename__ = "user_kpi_types"

    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
        primary_key=True,
    )
    kpi_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.kpi_types.kpi_type_id"),
        primary_key=True,
    )
    is_favorited: Mapped[bool] = mapped_column(server_default="false")

    __table_args__ = {"schema": "admin"}


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
        primary_key=True,
    )
    operational_project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
        primary_key=True,
    )
    notifications: Mapped[bool] = mapped_column(server_default="false")
    reports: Mapped[bool] = mapped_column(server_default="false")
    event_chat_notifications: Mapped[bool] = mapped_column(server_default="true")

    __table_args__ = {"schema": "admin"}


class NotificationSeverityLookup(Base):
    __tablename__ = "notification_severities"

    notification_severity_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=False
    )
    name_short: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "admin"}


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    notification_channel_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=False
    )
    name_short: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "admin"}


class NotificationStateLookup(Base):
    __tablename__ = "notification_state_enums"

    notification_state_enum_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=False
    )
    name_short: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "admin"}


class NotificationType(Base):
    __tablename__ = "notification_types"

    notification_type_id: Mapped[int] = mapped_column(primary_key=True)
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]
    in_app_enabled_default: Mapped[bool]
    email_enabled_default: Mapped[bool]
    in_app_severity_default: Mapped[enumerations.NotificationSeverity | None] = (
        mapped_column(notification_severity_enum)
    )
    in_app_severity_id_default: Mapped[int | None] = mapped_column(
        sa.ForeignKey(NotificationSeverityLookup.notification_severity_id),
    )
    email_severity_default: Mapped[enumerations.NotificationSeverity | None] = (
        mapped_column(notification_severity_enum)
    )
    email_severity_id_default: Mapped[int | None] = mapped_column(
        sa.ForeignKey(NotificationSeverityLookup.notification_severity_id),
    )

    __table_args__ = {"schema": "admin"}


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    notification_preference_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
    )
    notification_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("admin.notification_types.notification_type_id"),
    )
    in_app_enabled: Mapped[bool]
    email_enabled: Mapped[bool]
    email_min_severity: Mapped[enumerations.NotificationSeverity] = mapped_column(
        notification_severity_enum
    )
    email_min_severity_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey(NotificationSeverityLookup.notification_severity_id),
    )
    in_app_min_severity: Mapped[enumerations.NotificationSeverity] = mapped_column(
        notification_severity_enum
    )
    in_app_min_severity_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey(NotificationSeverityLookup.notification_severity_id),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "user_id",
            "project_id",
            "notification_type_id",
        ),
        {"schema": "admin"},
    )


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
    )
    notification_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("admin.notification_types.notification_type_id"),
    )
    data: Mapped[dict] = mapped_column(JSONB)
    severity: Mapped[enumerations.NotificationSeverity] = mapped_column(
        notification_severity_enum
    )
    severity_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey(NotificationSeverityLookup.notification_severity_id),
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    sent_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(server_default="true")

    __table_args__ = {"schema": "admin"}


class NotificationState(Base):
    __tablename__ = "notification_states"

    notification_state_id: Mapped[int] = mapped_column(primary_key=True)
    notification_id: Mapped[int] = mapped_column(
        sa.ForeignKey("admin.notifications.notification_id"),
    )
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
    )
    channel: Mapped[enumerations.NotificationChannelEnum] = mapped_column(
        notification_channel_enum
    )
    channel_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey(NotificationChannel.notification_channel_id),
    )
    state: Mapped[enumerations.NotificationStateEnum] = mapped_column(
        notification_state_enum
    )
    state_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey(NotificationStateLookup.notification_state_enum_id),
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "notification_id",
            "user_id",
            "channel",
        ),
        {"schema": "admin"},
    )


class UserType(Base):
    __tablename__ = "user_types"

    user_type_id: Mapped[enumerations.UserTypeEnum] = mapped_column(
        SmallInteger,
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "admin"}


class UserProjectSettings(Base):
    __tablename__ = "user_project_settings"

    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id", ondelete="CASCADE"),
        primary_key=True,
    )
    settings: Mapped[dict] = mapped_column(JSONB)

    __table_args__ = {"schema": "admin"}


class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        insert_default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
    )
    name_long: Mapped[str]
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        onupdate=sa.func.now(),
        server_default=sa.func.now(),
    )

    company = relationship("Company", back_populates="teams")
    members = relationship("TeamMember", back_populates="team")

    __table_args__ = (
        sa.UniqueConstraint("company_id", "name_long"),
        {"schema": "admin"},
    )


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.teams.team_id"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
        primary_key=True,
    )

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")

    __table_args__ = {"schema": "admin"}


class SharedPages(Base):
    __tablename__ = "shared_pages"

    page_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    page_url: Mapped[str] = mapped_column(sa.Text, unique=True)
    page_slug: Mapped[str] = mapped_column(sa.Text, unique=True)
    password_hash: Mapped[str] = mapped_column(sa.Text)
    created_date: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=func.now(),
    )
    created_by: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    __table_args__ = {"schema": "admin"}


class ReactionType(Base):
    __tablename__ = "reaction_types"

    reaction_type_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name_short: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "admin"}


##### END ADMIN SCHEMA #####
