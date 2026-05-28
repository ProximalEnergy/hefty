"""SQLAlchemy project schema models."""

import datetime
import uuid

import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy import Enum
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core import enumerations
from core.database import Base

from .common import LTree, claim_status_enum, claim_update_type_enum


##### START PROJECT SCHEMA #####
# NOTE: Models without explicit schema use Base.metadata's default project schema.
class Device(Base):
    __tablename__ = "devices"

    device_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    device_id_path: Mapped[str | None] = mapped_column(LTree)
    device_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.device_types.device_type_id"),
    )
    device_model_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.device_models.device_model_id"),
    )
    cec_pv_inverter_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.cec_pv_inverters.cec_pv_inverter_id"),
    )
    cec_pv_module_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.cec_pv_modules.cec_pv_module_id"),
    )
    pv_module_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.pv_modules.pv_module_id"),
    )
    parent_device_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("project.devices.device_id"),
    )
    logical: Mapped[bool] = mapped_column(default=False)
    name_short: Mapped[str | None]
    name_long: Mapped[str | None]
    capacity_dc: Mapped[float | None] = mapped_column(sa.REAL)
    capacity_ac: Mapped[float | None] = mapped_column(sa.REAL)
    capacity_energy_dc: Mapped[float | None] = mapped_column(sa.REAL)
    capacity_power_ac_kw: Mapped[float | None] = mapped_column(sa.REAL)
    capacity_power_dc_kw: Mapped[float | None] = mapped_column(sa.REAL)
    capacity_energy_dc_kwh: Mapped[float | None] = mapped_column(sa.REAL)
    point: Mapped[Geography | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
    )
    polygon: Mapped[Geography | None] = mapped_column(
        Geography(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
    )
    serial_number: Mapped[str | None]

    sa.Index("ix_devices_device_type_id", device_type_id)
    sa.Index("ix_devices_device_id_path", device_id_path, postgresql_using="gist")

    device_type = relationship("DeviceType")


class PVDCCombiner(Base):
    __tablename__ = "pv_dc_combiners"

    device_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.devices.device_id"),
        primary_key=True,
    )
    pv_module_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.pv_modules.pv_module_id"),
    )
    modules_per_pv_source_circuit: Mapped[int] = mapped_column(sa.SmallInteger)
    modules_per_combiner: Mapped[int] = mapped_column(sa.SmallInteger)


class Tag(Base):
    __tablename__ = "tags"

    tag_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    in_tsdb: Mapped[bool] = mapped_column(server_default="FALSE")
    device_id: Mapped[int] = mapped_column(sa.ForeignKey("project.devices.device_id"))
    sensor_type_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.sensor_types.sensor_type_id"),
    )
    pg_data_type_id: Mapped[int] = mapped_column(
        sa.SmallInteger,
        sa.ForeignKey("operational.pg_data_types.pg_data_type_id"),
        server_default="0",
    )
    data_type_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.data_types.data_type_id"),
    )
    name_short: Mapped[str | None]
    name_long: Mapped[str | None]
    name_scada: Mapped[str] = mapped_column(unique=True)
    scada_id: Mapped[int | None]
    scada_type: Mapped[str | None]
    unit_scada: Mapped[str | None]
    unit_offset: Mapped[float | None] = mapped_column(sa.Double)
    unit_scale: Mapped[float | None] = mapped_column(sa.Double)
    status_lookup_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.status_lookup.status_lookup_id"),
    )
    point: Mapped[Geography | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
    )
    polygon: Mapped[Geography | None] = mapped_column(
        Geography(geometry_type="GEOMETRY", srid=4326, spatial_index=False),
    )

    sa.Index("ix_tags_in_tsdb", in_tsdb)

    device = relationship("Device")
    sensor_type = relationship("SensorType")
    data_type = relationship("DataType")


class DataExpected(Base):
    __tablename__ = "data_expected"

    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    device_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.devices.device_id"),
        primary_key=True,
    )
    expected_metric_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.expected_metrics.expected_metric_id"),
        primary_key=True,
    )
    value: Mapped[float]
    confidence_tier: Mapped[int | None]
    confidence_codes: Mapped[str | None]
    version: Mapped[str | None]

    sa.Index("data_expected_time_idx", time.desc())  # Auto-generated by Timescale

    # NOTE: Timescale Hypertable is created in the alembic migration


class ForecastMet(Base):
    __tablename__ = "forecast_met"

    forecast_weather_model_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.forecast_weather_models.forecast_weather_model_id"),
        primary_key=True,
    )
    time_forecast_run: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    time_forecasted: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    ghi: Mapped[float] = mapped_column(
        sa.Float,
        comment="Global horizontal irradiance [W/m^2]",
    )
    dhi: Mapped[float] = mapped_column(
        sa.Float,
        comment="Diffuse horizontal irradiance [W/m^2]",
    )
    dni: Mapped[float] = mapped_column(
        sa.Float,
        comment="Direct normal irradiance [W/m^2]",
    )
    ambient_temperature: Mapped[float] = mapped_column(
        sa.Float,
        comment="Ambient air temperature [C]",
    )
    wind_speed: Mapped[float] = mapped_column(
        sa.Float,
        comment="Wind speed [m/s]",
    )

    forecast_weather_model = relationship("ForecastWeatherModel")


class ForecastMetLatest(Base):
    __tablename__ = "forecast_met_latest"

    forecast_weather_model_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.forecast_weather_models.forecast_weather_model_id"),
        primary_key=True,
    )
    time_forecast_run: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
    )
    time_forecasted: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    ghi: Mapped[float] = mapped_column(
        sa.Float,
        comment="Global horizontal irradiance [W/m^2]",
    )
    dhi: Mapped[float] = mapped_column(
        sa.Float,
        comment="Diffuse horizontal irradiance [W/m^2]",
    )
    dni: Mapped[float] = mapped_column(
        sa.Float,
        comment="Direct normal irradiance [W/m^2]",
    )
    ambient_temperature: Mapped[float] = mapped_column(
        sa.Float,
        comment="Ambient air temperature [C]",
    )
    wind_speed: Mapped[float] = mapped_column(
        sa.Float,
        comment="Wind speed [m/s]",
    )

    sa.Index("forecast_met_latest_time_forecasted_idx", time_forecasted)

    forecast_weather_model = relationship("ForecastWeatherModel")


class ForecastPVEnergy(Base):
    __tablename__ = "forecast_pv_energy"

    forecast_weather_model_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.forecast_weather_models.forecast_weather_model_id"),
        primary_key=True,
    )
    time_forecast_run: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    time_forecasted: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    p_mp: Mapped[float] = mapped_column(
        sa.Float,
        comment="PV output power at POI [W]",
    )

    forecast_weather_model = relationship("ForecastWeatherModel")


class ForecastPVEnergyLatest(Base):
    __tablename__ = "forecast_pv_energy_latest"

    forecast_weather_model_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.forecast_weather_models.forecast_weather_model_id"),
        primary_key=True,
    )
    time_forecast_run: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
    )
    time_forecasted: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    p_mp: Mapped[float] = mapped_column(
        sa.Float,
        comment="PV output power at POI [W]",
    )

    sa.Index("forecast_pv_energy_latest_time_forecasted_idx", time_forecasted)

    forecast_weather_model = relationship("ForecastWeatherModel")


class ForecastAvailablePVEnergy(Base):
    __tablename__ = "forecast_available_pv_energy"

    forecast_weather_model_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.forecast_weather_models.forecast_weather_model_id"),
        primary_key=True,
    )
    time_forecast_run: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    time_forecasted: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    p_mp: Mapped[float] = mapped_column(
        sa.Float,
        comment="Available PV output power at POI [W]",
    )

    forecast_weather_model = relationship("ForecastWeatherModel")


class ForecastAvailablePVEnergyLatest(Base):
    __tablename__ = "forecast_available_pv_energy_latest"

    forecast_weather_model_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.forecast_weather_models.forecast_weather_model_id"),
        primary_key=True,
    )
    time_forecast_run: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
    )
    time_forecasted: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    p_mp: Mapped[float] = mapped_column(
        sa.Float,
        comment="Available PV output power at POI [W]",
    )

    sa.Index("forecast_available_pv_energy_latest_time_forecasted_idx", time_forecasted)

    forecast_weather_model = relationship("ForecastWeatherModel")


class ProjectDataTimeseries(Base):
    __tablename__ = "data_timeseries"

    # NOTE: SQLAlchemy requires at least one primary key for each table.
    # This removes the need for a unique constraint on the time and tag_id columns.
    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.tags.tag_id"),
        primary_key=True,
    )
    value_integer: Mapped[int | None] = mapped_column(sa.Integer)
    value_bigint: Mapped[int | None] = mapped_column(sa.BigInteger)
    value_real: Mapped[float | None] = mapped_column(sa.REAL)
    value_double: Mapped[float | None] = mapped_column(sa.Double)
    value_boolean: Mapped[bool | None] = mapped_column()
    value_text: Mapped[str | None] = mapped_column(sa.Text)

    __table_args__ = (
        sa.Index(f"{__tablename__}_tag_id_time_idx", tag_id, time.desc()),
        sa.Index(f"{__tablename__}_time_idx", time.desc()),
    )


class DataRaw(Base):
    __tablename__ = "data_raw"

    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.tags.tag_id"),
        primary_key=True,
    )
    value_continuous: Mapped[float | None] = mapped_column(sa.Double)
    value_boolean: Mapped[bool | None] = mapped_column(sa.Boolean)
    value_cumulative: Mapped[int | None] = mapped_column(sa.BigInteger)
    value_string: Mapped[str | None] = mapped_column(sa.String)
    value_status: Mapped[int | None]

    sa.Index("data_raw_time_idx", time.desc())  # Auto-generated by Timescale
    sa.Index("data_raw_tag_id_time_idx", tag_id, time.desc())


class Data(Base):
    __tablename__ = "data"

    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.tags.tag_id"),
        primary_key=True,
    )
    value_continuous: Mapped[float | None] = mapped_column(sa.Double)
    value_boolean: Mapped[bool | None] = mapped_column(sa.Boolean)
    value_cumulative: Mapped[int | None] = mapped_column(sa.BigInteger)
    value_string: Mapped[str | None] = mapped_column(sa.String)
    value_status: Mapped[int | None]

    sa.Index("data_time_idx", time.desc())


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.devices.device_id"),
        index=True,
    )
    failure_mode_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.failure_modes.failure_mode_id"),
        server_default="1",
    )
    root_cause_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.root_causes.root_cause_id"),
    )
    time_start: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))
    time_end: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    time_detected: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
    )
    time_last_analyzed: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
    )
    loss_total_financial: Mapped[float | None] = mapped_column(sa.Double)
    loss_daily_financial: Mapped[float | None] = mapped_column(sa.Double)
    version: Mapped[str | None]

    device = relationship("Device")
    failure_mode = relationship("FailureMode")
    root_cause = relationship("RootCause")


class Event2(Base):
    __tablename__ = "events_2"

    event_id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.devices.device_id"),
        index=True,
    )
    failure_mode_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.failure_modes.failure_mode_id"),
        server_default="1",
    )
    root_cause_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.root_causes.root_cause_id"),
    )
    time_start: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))
    time_end: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    time_detected: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
    )
    time_last_analyzed: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
    )
    loss_total_financial: Mapped[float | None] = mapped_column(sa.Double)
    version: Mapped[str | None]

    device = relationship("Device")
    failure_mode = relationship("FailureMode")
    root_cause = relationship("RootCause")

    __table_args__ = (sa.UniqueConstraint("device_id", "time_start"),)


class Issue(Base):
    __tablename__ = "issues"

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.devices.device_id"),
        index=True,
    )
    tag_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("project.tags.tag_id"),
        nullable=True,
    )
    issue_category_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.issue_categories.issue_category_id"),
    )
    time_start: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))
    time_end: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    detector_metadata: Mapped[dict | None] = mapped_column(JSONB)

    device = relationship("Device")
    tag = relationship("Tag")
    issue_category = relationship("IssueCategory")


class IssueUpdate(Base):
    __tablename__ = "issue_updates"

    issue_update_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    issue_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.issues.issue_id", ondelete="CASCADE"),
    )
    issue_state_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.issue_states.issue_state_id"),
    )
    state_time_start: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
    )
    state_changed_source: Mapped[str] = mapped_column(sa.String)

    issue = relationship("Issue")
    issue_state = relationship("IssueState")


class EventLoss(Base):
    __tablename__ = "event_losses"

    event_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    event_loss_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.event_loss_types.event_loss_type_id"),
        primary_key=True,
    )
    loss: Mapped[float] = mapped_column(sa.Double)
    version: Mapped[str | None]

    sa.Index("ix_event_id_time_desc", event_id, time.desc())
    sa.Index("event_losses_time_idx", time.desc())


class EventLoss2(Base):
    __tablename__ = "event_losses_2"

    event_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.events_2.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    event_loss_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.event_loss_types.event_loss_type_id"),
        primary_key=True,
    )
    loss: Mapped[float] = mapped_column(sa.Double)
    version: Mapped[str | None]

    sa.Index("ix_event_id_time_desc_2", event_id, time.desc())
    sa.Index("event_losses_2_time_idx", time.desc())


class EventMessage(Base):
    __tablename__ = "event_messages"

    event_message_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.events.event_id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(sa.ForeignKey("admin.users.user_id"))
    body: Mapped[str] = mapped_column(sa.Text)
    mentions: Mapped[str | None]
    parent_message_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("project.event_messages.event_message_id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))
    edited_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    image_s3_keys: Mapped[str | None]
    private: Mapped[bool] = mapped_column(
        sa.Boolean(), server_default="false", nullable=False
    )

    event = relationship("Event")
    user = relationship("User")
    parent_message = relationship(
        "EventMessage", remote_side="EventMessage.event_message_id"
    )
    images = relationship("EventMessageImage", back_populates="event_message")
    reactions = relationship("EventMessageReaction", back_populates="event_message")

    sa.Index(
        "event_messages_event_id_created_at_idx",
        event_id,
        created_at.desc(),
    )
    sa.Index("event_messages_parent_message_id_idx", parent_message_id)


class EventMessageImage(Base):
    __tablename__ = "event_message_images"

    event_message_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_message_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.event_messages.event_message_id", ondelete="CASCADE")
    )
    event_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.events.event_id", ondelete="CASCADE")
    )
    s3_key: Mapped[str]
    filename: Mapped[str]
    content_type: Mapped[str]
    file_size: Mapped[int]
    created_at: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))

    event_message = relationship("EventMessage", back_populates="images")
    event = relationship("Event")

    sa.Index("event_message_images_event_message_id_idx", event_message_id)
    sa.Index("event_message_images_event_id_idx", event_id)


class EventMessageReaction(Base):
    __tablename__ = "event_message_reactions"

    reaction_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_message_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.event_messages.event_message_id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(sa.ForeignKey("admin.users.user_id"))
    reaction_type: Mapped[enumerations.ReactionTypeEnum] = mapped_column(
        Enum(enumerations.ReactionTypeEnum, name="reactiontype")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))

    event_message = relationship("EventMessage", back_populates="reactions")
    user = relationship("User")

    sa.Index("event_message_reactions_event_message_id_idx", event_message_id)
    sa.UniqueConstraint(
        "event_message_id",
        "user_id",
        "reaction_type",
        name="uq_event_message_reactions_message_user_type",
    )


class EventChatMute(Base):
    __tablename__ = "event_chat_mutes"

    event_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"), primary_key=True
    )
    muted_at: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))

    event = relationship("Event")
    user = relationship("User")

    sa.Index("event_chat_mutes_user_id_idx", user_id)


class Report(Base):
    __tablename__ = "reports"

    report_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.report_types.report_type_id"),
        primary_key=True,
    )
    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    time_generated: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True))
    data_pdf: Mapped[bytes | None] = mapped_column(BYTEA)

    report_type = relationship("ReportType")


class CMMSTicket(Base):
    __tablename__ = "cmms_tickets"

    cmms_ticket_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cmms_integration_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.cmms_integrations.cmms_integration_id"),
    )
    db_created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),  # Only set on INSERT
    )
    db_updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),  # Set on INSERT
        onupdate=sa.func.now(),  # Update on every UPDATE
    )
    source_id: Mapped[int]
    key: Mapped[str]
    source_created_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    due_date: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    summary: Mapped[str | None]
    summary_long: Mapped[str | None]
    status: Mapped[str | None]
    status_change_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    priority: Mapped[str | None]
    reporter: Mapped[str | None]
    assigned_to: Mapped[str | None]
    location: Mapped[str | None]
    cmms_device_id: Mapped[str | None]
    cmms_device_name: Mapped[str | None]
    link: Mapped[str | None]

    json_raw: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        sa.UniqueConstraint(
            "cmms_integration_id",
            "source_id",
            name="cmms_tickets_integration_source_unique",
        ),
    )


class DataTimeseriesLast(Base):
    __tablename__ = "data_timeseries_last"

    tag_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.tags.tag_id"),
        primary_key=True,
    )
    time: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime(timezone=True))
    value_integer: Mapped[int | None] = mapped_column(sa.Integer)
    value_bigint: Mapped[int | None] = mapped_column(sa.BigInteger)
    value_real: Mapped[float | None] = mapped_column(sa.REAL)
    value_double: Mapped[float | None] = mapped_column(sa.Double)
    value_boolean: Mapped[bool | None] = mapped_column()
    value_text: Mapped[str | None] = mapped_column(sa.Text)

    tag = relationship("Tag")


class CMMSDevice(Base):
    __tablename__ = "cmms_devices"

    device_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.devices.device_id"),
        primary_key=True,
    )
    cmms_device_id: Mapped[str] = mapped_column(primary_key=True)
    cmms_integration_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.cmms_integrations.cmms_integration_id"),
        primary_key=True,
    )

    device = relationship("Device")


class DroneInspection(Base):
    __tablename__ = "drone_inspections"

    inspection_uuid: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    inspection_time: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
    )
    upload_time: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
    )
    service_tier: Mapped[str | None]
    total_power_loss_kw: Mapped[float | None]
    total_power_loss_percent: Mapped[float | None]
    total_affected_modules: Mapped[int | None]
    report_summary: Mapped[str | None]

    anomalies = relationship("DroneAnomaly", back_populates="inspection")


class DroneAnomaly(Base):
    __tablename__ = "drone_anomalies"

    anomaly_uuid: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    inspection_uuid: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("project.drone_inspections.inspection_uuid"),
        index=True,
    )
    event_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("project.events.event_id"),
        index=True,
    )
    stack_id: Mapped[str | None]
    ir_signal: Mapped[str | None]
    rgb_signal: Mapped[str | None]
    ir_image_url: Mapped[str | None]
    rgb_image_url: Mapped[str | None]
    subsystem: Mapped[str | None]
    remediation_category: Mapped[str | None]
    energy_loss_weighting: Mapped[float | None]
    power_loss_kw: Mapped[float | None]
    location_lat: Mapped[float | None]
    location_lon: Mapped[float | None]
    client_status_id: Mapped[int | None]

    inspection = relationship("DroneInspection", back_populates="anomalies")
    event = relationship("Event")


class UniqueTagPatterns(Base):
    __tablename__ = "unique_tag_patterns"

    pattern: Mapped[str] = mapped_column(primary_key=True)
    count: Mapped[int] = mapped_column(sa.Integer)
    example_tag_ids: Mapped[dict] = mapped_column(JSONB)


class EventCMMSTicket(Base):
    __tablename__ = "event_cmms_tickets"

    event_cmms_ticket_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    event_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.events.event_id"), index=True
    )
    cmms_ticket_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.cmms_tickets.cmms_ticket_id"), index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"), index=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    event = relationship("Event")
    cmms_ticket = relationship("CMMSTicket")

    __table_args__ = (sa.UniqueConstraint("event_id", "cmms_ticket_id"),)


class Claim(Base):
    __tablename__ = "claims"

    claim_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    claim_config_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.claim_configs.claim_config_id"),
    )
    status: Mapped[enumerations.ClaimStatus] = mapped_column(claim_status_enum)
    summary: Mapped[str | None]
    external_reference: Mapped[str | None]

    claim_config = relationship("ClaimConfig")
    devices = relationship(
        "ClaimDevice",
        back_populates="claim",
        lazy="selectin",
        order_by="ClaimDevice.claim_device_id",
    )
    updates = relationship(
        "ClaimUpdate",
        back_populates="claim",
        lazy="selectin",
        order_by="ClaimUpdate.created_at",
    )
    attachments = relationship(
        "ClaimAttachment",
        back_populates="claim",
        lazy="selectin",
        order_by="ClaimAttachment.uploaded_at",
    )


class ClaimDevice(Base):
    __tablename__ = "claim_devices"

    claim_device_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    claim_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.claims.claim_id"),
    )
    device_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.devices.device_id"),
    )
    event_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("project.events.event_id"),
        nullable=True,
    )
    oem_serial_number: Mapped[str | None]
    oem_part_number: Mapped[str | None]
    notes: Mapped[str | None]

    claim = relationship("Claim", back_populates="devices")
    device = relationship("Device")
    event = relationship(
        "Event",
        primaryjoin="ClaimDevice.event_id == Event.event_id",
    )


class ClaimUpdate(Base):
    __tablename__ = "claim_updates"

    claim_update_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    claim_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.claims.claim_id"),
    )
    update_type: Mapped[enumerations.ClaimUpdateType] = mapped_column(
        claim_update_type_enum,
    )
    from_status: Mapped[enumerations.ClaimStatus | None] = mapped_column(
        claim_status_enum,
        nullable=True,
    )
    to_status: Mapped[enumerations.ClaimStatus | None] = mapped_column(
        claim_status_enum,
        nullable=True,
    )
    message: Mapped[str | None]
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )

    claim = relationship("Claim", back_populates="updates")
    user = relationship("User")
    attachments = relationship(
        "ClaimAttachment",
        back_populates="claim_update",
        lazy="selectin",
    )


class ClaimAttachment(Base):
    __tablename__ = "claim_attachments"

    claim_attachment_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    claim_id: Mapped[int] = mapped_column(
        sa.ForeignKey("project.claims.claim_id", ondelete="CASCADE"),
    )
    claim_update_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey(
            "project.claim_updates.claim_update_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    s3_key: Mapped[str]
    filename: Mapped[str]
    content_type: Mapped[str | None]
    uploaded_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )

    claim = relationship("Claim", back_populates="attachments")
    claim_update = relationship("ClaimUpdate", back_populates="attachments")

    __table_args__ = (
        sa.UniqueConstraint(
            "claim_id",
            "filename",
            name="uq_claim_attachments_claim_filename",
        ),
        sa.UniqueConstraint(
            "s3_key",
            name="uq_claim_attachments_s3_key",
        ),
        sa.Index(
            "ix_claim_attachments_claim_update_id",
            "claim_update_id",
        ),
    )


##### END PROJECT SCHEMA #####
