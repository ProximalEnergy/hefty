"""SQLAlchemy operational schema models."""

import datetime
import uuid

import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy import Enum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core import enumerations
from core.database import Base

from .common import claim_submission_channel_enum


##### START OPERATIONAL SCHEMA #####
# NOTE: Every model in the operational schema
# must specify `__table_args__ = {"schema": "operational"}`
class PGDataType(Base):
    __tablename__ = "pg_data_types"

    pg_data_type_id: Mapped[int] = mapped_column(
        sa.SmallInteger,
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str] = mapped_column(sa.Text, unique=True)

    __table_args__ = {"schema": "operational"}


class DataType(Base):
    __tablename__ = "data_types"

    data_type_id: Mapped[int] = mapped_column(
        sa.SmallInteger,
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "operational"}


class DeviceType(Base):
    __tablename__ = "device_types"

    device_type_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]

    __table_args__ = {"schema": "operational"}

    def __str__(self):
        """Return the human-readable device type name."""
        return self.name_long


class DeviceModel(Base):
    __tablename__ = "device_models"

    device_model_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.device_types.device_type_id"),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
    )
    brand: Mapped[str]
    model: Mapped[str]

    device_type = relationship("DeviceType")

    __table_args__ = (
        sa.UniqueConstraint(
            "company_id",
            "device_type_id",
            "model",
            name="uq_device_models_company_id_device_type_id_model",
        ),
        {"schema": "operational"},
    )

    def __str__(self):
        """Return the device model's brand and model label."""
        return f"{self.brand} {self.model}"


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
    )
    s3_key: Mapped[str]
    openai_file_id: Mapped[str]

    __table_args__ = {"schema": "operational"}


class ContractCategory(Base):
    __tablename__ = "contract_categories"

    contract_category_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]
    description: Mapped[str | None] = mapped_column(sa.Text)

    __table_args__ = {"schema": "operational"}


class Contract(Base):
    __tablename__ = "contracts"

    contract_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.documents.document_id"),
        unique=True,
    )
    company_id_provider: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
    )
    company_id_counter: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
    )
    execution_date: Mapped[datetime.date]
    contract_category_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.contract_categories.contract_category_id")
    )
    term_start_date: Mapped[datetime.date | None]
    term_end_date: Mapped[datetime.date | None]
    counter_contact_addressee: Mapped[str | None]
    counter_contact_email: Mapped[str | None]
    counter_contact_address: Mapped[str | None] = mapped_column(sa.Text)
    contract_summary: Mapped[str | None] = mapped_column(sa.Text)
    contract_kpis = relationship("ContractKPI", back_populates="contract")
    contract_category = relationship("ContractCategory")

    __table_args__ = {"schema": "operational"}


class ContractKPI(Base):
    __tablename__ = "contract_kpis"

    contract_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.contracts.contract_id"),
        primary_key=True,
    )
    kpi_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.kpi_types.kpi_type_id"),
        primary_key=True,
    )
    threshold: Mapped[dict | None] = mapped_column(JSONB)
    liquidated_damages: Mapped[dict | None] = mapped_column(JSONB)
    claim_howto: Mapped[dict | None] = mapped_column(JSONB)
    provider_responsible: Mapped[bool | None]

    # Add the back reference to Contract
    contract = relationship("Contract", back_populates="contract_kpis")
    # Add the relationship to KPIType
    kpi_type = relationship("KPIType")

    __table_args__ = {"schema": "operational"}


class ClaimConfig(Base):
    __tablename__ = "claim_configs"

    claim_config_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    submitter_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("admin.companies.company_id"),
    )
    counterparty_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("admin.companies.company_id"),
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("operational.projects.project_id"),
        nullable=True,
    )
    default_submission_channel: Mapped[enumerations.ClaimSubmissionChannel] = (
        mapped_column(claim_submission_channel_enum)
    )
    default_contact: Mapped[str | None]
    portal_url: Mapped[str | None]

    submitter_company = relationship("Company", foreign_keys=[submitter_company_id])
    counterparty_company = relationship(
        "Company",
        foreign_keys=[counterparty_company_id],
    )
    project = relationship("Project")

    __table_args__ = {"schema": "operational"}


class OMContractorScope(Base):
    __tablename__ = "om_contractor_scopes"

    om_contractor_scope_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
    )
    scope_json: Mapped[dict] = mapped_column(
        JSONB, server_default='{"device_type_ids": []}'
    )
    contractor_addressee: Mapped[str | None]
    contractor_email: Mapped[str | None]
    contractor_phone: Mapped[str | None]

    __table_args__ = (
        sa.CheckConstraint(
            "contractor_phone IS NULL OR contractor_phone ~ '^\\+?[1-9][0-9]{1,14}$'",
            name="chk_om_contractor_phone_e164",
        ),
        {"schema": "operational"},
    )


class EventLossType(Base):
    __tablename__ = "event_loss_types"

    event_loss_type_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str]

    __table_args__ = {"schema": "operational"}


class ExpectedVersions(Base):
    __tablename__ = "expected_versions"

    expected_version_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    major: Mapped[int]
    minor: Mapped[int]
    patch: Mapped[int]

    __table_args__ = (
        sa.UniqueConstraint(
            "major",
            "minor",
            "patch",
            name="unique_expected_version",
        ),
        {"schema": "operational"},
    )


class ExpectedMetric(Base):
    __tablename__ = "expected_metrics"

    expected_metric_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=False,
    )
    expected_metric_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.expected_metric_types.expected_metric_type_id"),
    )
    includes_soiling: Mapped[bool] = mapped_column(server_default="FALSE")
    includes_warranted_degradation: Mapped[bool] = mapped_column(server_default="TRUE")

    __table_args__ = (
        sa.UniqueConstraint(
            "expected_metric_type_id",
            "includes_soiling",
            "includes_warranted_degradation",
            name="uq_expected_metric",
        ),
        {"schema": "operational"},
    )


class ExpectedMetricType(Base):
    __tablename__ = "expected_metric_types"

    expected_metric_type_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]

    __table_args__ = {"schema": "operational"}


class FailureMode(Base):
    __tablename__ = "failure_modes"

    failure_mode_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    device_type_id: Mapped[int] = mapped_column(
        sa.SmallInteger,
        sa.ForeignKey("operational.device_types.device_type_id"),
    )
    name_short: Mapped[str]
    name_long: Mapped[str]

    __table_args__ = {"schema": "operational"}


class IssueCategory(Base):
    __tablename__ = "issue_categories"

    issue_category_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=False
    )
    name_long: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "operational"}

    def __str__(self):
        """Return the human-readable issue category name."""
        return self.name_long


class IssueState(Base):
    __tablename__ = "issue_states"

    issue_state_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name_long: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "operational"}

    def __str__(self):
        """Return the human-readable issue category name."""
        return self.name_long


class StatusLookup(Base):
    __tablename__ = "status_lookup"

    status_lookup_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]
    status_binary_id: Mapped[int | None]
    status_string_id: Mapped[int | None]
    status_boolean_id: Mapped[int | None]

    __table_args__ = {"schema": "operational"}


class StatusBinary(Base):
    __tablename__ = "status_binary"

    status_binary_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    bit_position: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str]
    state_false: Mapped[str | None]
    state_true: Mapped[str | None]
    nominal_state: Mapped[bool | None]
    failure_mode_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.failure_modes.failure_mode_id"),
    )

    __table_args__ = {"schema": "operational"}


class StatusString(Base):
    __tablename__ = "status_string"

    status_string_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    string_trigger: Mapped[str] = mapped_column(primary_key=True)
    description: Mapped[str]
    failure_mode_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.failure_modes.failure_mode_id"),
    )

    __table_args__ = {"schema": "operational"}


class StatusBoolean(Base):
    __tablename__ = "status_boolean"

    status_boolean_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=False,
    )
    description: Mapped[str]
    state_false: Mapped[str | None]
    state_true: Mapped[str]
    nominal_state: Mapped[bool | None]
    failure_mode_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.failure_modes.failure_mode_id"),
    )

    __table_args__ = {"schema": "operational"}


class KPIInstance(Base):
    __tablename__ = "kpi_instances"

    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
        primary_key=True,
    )
    kpi_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.kpi_types.kpi_type_id"),
        primary_key=True,
    )
    is_visible: Mapped[bool] = mapped_column(server_default="FALSE")

    kpi_type = relationship("KPIType")
    project = relationship("Project")

    __table_args__ = {"schema": "operational"}


class KPIType(Base):
    __tablename__ = "kpi_types"

    kpi_type_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    device_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.device_types.device_type_id"),
    )
    project_type_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.project_types.project_type_id"),
    )
    name_short: Mapped[str]
    name_long: Mapped[str]
    name_metric: Mapped[str]
    description: Mapped[str | None]
    unit: Mapped[str | None]
    aggregation_method: Mapped[str]
    doc_url: Mapped[str | None]
    critical_low: Mapped[float | None]
    warning_low: Mapped[float | None]
    warning_high: Mapped[float | None]
    critical_high: Mapped[float | None]

    device_type = relationship("DeviceType")
    __table_args__ = {"schema": "operational"}

    def __str__(self):
        """Return the human-readable KPI type name."""
        return self.name_long


class OperationalDataTimeseries(Base):
    __tablename__ = "data_timeseries"

    # NOTE: SQLAlchemy requires at least one primary key for each table.
    # This removes the need for a unique constraint on the time and tag_id columns.
    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(primary_key=True)
    sensor_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.sensor_types.sensor_type_id"),
        primary_key=True,
    )
    value_integer: Mapped[int | None] = mapped_column(sa.Integer)
    value_bigint: Mapped[int | None] = mapped_column(sa.BigInteger)
    value_real: Mapped[float | None] = mapped_column(sa.REAL)
    value_double: Mapped[float | None] = mapped_column(sa.Double)
    value_boolean: Mapped[bool | None] = mapped_column()
    value_text: Mapped[str | None] = mapped_column(sa.Text)

    __table_args__ = (
        sa.Index(f"{__tablename__}_time_idx", time.desc()),
        {"schema": "operational"},
    )


class OperationalKPIData(Base):
    __tablename__ = "kpi_data"

    date: Mapped[datetime.date] = mapped_column(primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
        primary_key=True,
    )
    kpi_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.kpi_types.kpi_type_id"),
        primary_key=True,
    )
    device_data_json: Mapped[dict | None] = mapped_column(JSONB)
    project_data: Mapped[float]
    version: Mapped[str | None]
    updated_at: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))

    # NOTE: A Postgres trigger will update the updated_at column on insert/update

    __table_args__ = (
        # Query by project_id, kpi_type_id, and date range
        sa.Index(
            "kpi_data_project_id_kpi_type_id_date_idx",
            project_id,
            kpi_type_id,
            date.desc(),
        ),
        # Query by project_id and date range
        sa.Index(
            "kpi_data_project_id_date_idx",
            project_id,
            date.desc(),
        ),
        # Query by kpi_type_id and date range
        sa.Index(
            "kpi_data_kpi_type_id_date_idx",
            kpi_type_id,
            date.desc(),
        ),
        {"schema": "operational"},
    )


class ProjectStatusTypes(Base):
    __tablename__ = "project_status_types"
    project_status_type_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "operational"}


class Project(Base):
    """
    Attributes:
        data_receive_schedule: Cron-style string specifying when to expect data
            to be received (e.g. '*/5 * * * *' for every 5 minutes).
        has_expected_energy_integration: Whether the project has an expected energy
            integration.
    """

    __tablename__ = "projects"

    project_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id_int: Mapped[int] = mapped_column(sa.SmallInteger, unique=True)
    project_type_id: Mapped[enumerations.ProjectTypeEnum] = mapped_column(
        sa.ForeignKey("operational.project_types.project_type_id"),
    )
    project_status_type_id: Mapped[enumerations.ProjectStatusType] = mapped_column(
        sa.ForeignKey("operational.project_status_types.project_status_type_id"),
        server_default=str(enumerations.ProjectStatusType.ONBOARDING),
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]
    data_table: Mapped[str]
    data_interval: Mapped[enumerations.ProjectDataInterval] = mapped_column(
        Enum(
            enumerations.ProjectDataInterval,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
        ),
        nullable=False,
    )
    data_cagg_interval: Mapped[str | None]
    data_receive_schedule: Mapped[str | None]
    commencement_of_construction_date: Mapped[datetime.date | None]
    financial_close_date: Mapped[datetime.date | None]
    notice_to_proceed_date: Mapped[datetime.date | None]
    mechanical_completion_date: Mapped[datetime.date | None]
    substantial_completion_date: Mapped[datetime.date | None]
    interconnection_approval_date: Mapped[datetime.date | None]
    performance_test_completion_date: Mapped[datetime.date | None]
    cod: Mapped[datetime.date | None]
    placed_in_service_date: Mapped[datetime.date | None]
    first_realtime_data_received_date: Mapped[datetime.date | None]
    first_data_backfilled_date: Mapped[datetime.date | None]
    address: Mapped[str]
    image_url: Mapped[str | None]
    point: Mapped[Geography] = mapped_column(
        Geography(
            geometry_type="POINT",
            srid=4326,
            spatial_index=False,
        ),
    )
    polygon: Mapped[Geography | None] = mapped_column(
        Geography(
            geometry_type="GEOMETRY",
            srid=4326,
            spatial_index=False,
        ),
    )
    elevation: Mapped[float] = mapped_column(sa.REAL, server_default="0")
    time_zone: Mapped[str]
    interconnecting_iso: Mapped[str | None]
    interconnecting_utility: Mapped[str | None]
    interconnecting_node_code: Mapped[str | None]
    interconnecting_substation: Mapped[str | None]
    interconnecting_voltage: Mapped[float | None] = mapped_column(sa.REAL)
    poi: Mapped[float] = mapped_column(sa.REAL)
    capacity_dc: Mapped[float] = mapped_column(sa.REAL)
    capacity_ac: Mapped[float] = mapped_column(sa.REAL)
    capacity_bess_power_ac: Mapped[float] = mapped_column(sa.REAL, server_default="0")
    capacity_bess_energy_bol_dc: Mapped[float] = mapped_column(
        sa.REAL, server_default="0"
    )
    has_event_integration: Mapped[bool] = mapped_column(server_default="FALSE")
    has_expected_energy_integration: Mapped[bool] = mapped_column(
        server_default="FALSE"
    )
    has_report_integration: Mapped[bool] = mapped_column(server_default="FALSE")
    has_quality_integration: Mapped[bool] = mapped_column(server_default="FALSE")
    has_block_layout: Mapped[bool] = mapped_column(server_default="FALSE")
    has_pv_pcs_layout: Mapped[bool] = mapped_column(server_default="FALSE")
    has_tracker_layout: Mapped[bool] = mapped_column(server_default="FALSE")
    has_pv_dc_combiner_layout: Mapped[bool] = mapped_column(server_default="FALSE")
    has_met_stations: Mapped[bool] = mapped_column(server_default="FALSE")
    has_pv_pcs_modules: Mapped[bool] = mapped_column(server_default="FALSE")
    has_pv_dc_combiners: Mapped[bool] = mapped_column(server_default="FALSE")
    has_trackers: Mapped[bool] = mapped_column(server_default="FALSE")
    has_bess_blocks: Mapped[bool] = mapped_column(server_default="FALSE")
    has_bess_pcss: Mapped[bool] = mapped_column(server_default="FALSE")
    has_bess_enclosures: Mapped[bool] = mapped_column(server_default="FALSE")
    has_bess_banks: Mapped[bool] = mapped_column(server_default="FALSE")
    has_bess_strings: Mapped[bool] = mapped_column(server_default="FALSE")
    has_backtracking: Mapped[bool | None] = mapped_column()
    has_real_time_data: Mapped[bool] = mapped_column(server_default="FALSE")
    ppa: Mapped[dict | None] = mapped_column(JSONB)
    spec: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    gsheet_id: Mapped[str | None]
    last_updated: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    last_updated_by: Mapped[str | None] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
    )
    owner: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
    )
    database_provider: Mapped[enumerations.ProjectDatabaseProvider] = mapped_column(
        sa.String, server_default=enumerations.ProjectDatabaseProvider.CLICKHOUSE
    )

    project_type = relationship("ProjectType")

    __table_args__ = {"schema": "operational"}

    def __str__(self):
        """Return the human-readable project name."""
        return self.name_long


class CalendarItem(Base):
    __tablename__ = "calendar_items"

    calendar_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    title: Mapped[str] = mapped_column(sa.Text)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    calendar_item_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("operational.calendar_item_categories.category_id"),
    )
    start_time: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))
    end_time: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    all_day: Mapped[bool] = mapped_column(server_default="FALSE")
    rrule: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    timezone: Mapped[str | None] = mapped_column(sa.Text, nullable=False)

    notify_offsets: Mapped[list[str] | None] = mapped_column(
        sa.ARRAY(sa.Text),
        nullable=True,
    )
    notify_method: Mapped[list[str] | None] = mapped_column(
        sa.ARRAY(sa.Text),
        nullable=True,
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("admin.companies.company_id"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("operational.projects.project_id"),
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    # Relationships
    company = relationship("Company")
    project = relationship("Project")
    category = relationship("CalendarItemCategory")
    exceptions = relationship(
        "CalendarItemException",
        back_populates="calendar_item",
        cascade="all, delete-orphan",
    )
    assignments = relationship(
        "CalendarItemAssignment",
        back_populates="calendar_item",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        sa.Index(
            f"{__tablename__}_project_id_start_time_idx",
            "project_id",
            "start_time",
        ),
        sa.Index(
            f"{__tablename__}_company_id_start_time_idx",
            "company_id",
            "start_time",
        ),
        {"schema": "operational"},
    )


class CalendarItemException(Base):
    __tablename__ = "calendar_item_exceptions"

    exception_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    calendar_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("operational.calendar_items.calendar_item_id"),
    )
    exception_date: Mapped[datetime.date] = mapped_column(sa.Date)
    is_cancelled: Mapped[bool] = mapped_column(server_default="FALSE")
    override_start_time: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    override_end_time: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    # Relationship
    calendar_item = relationship("CalendarItem", back_populates="exceptions")

    __table_args__ = (
        sa.UniqueConstraint(
            "calendar_item_id",
            "exception_date",
            name="uq_calendar_item_exception_date",
        ),
        {"schema": "operational"},
    )


class CalendarItemAssignment(Base):
    __tablename__ = "calendar_item_assignments"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    calendar_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("operational.calendar_items.calendar_item_id"),
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
        nullable=True,
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("admin.teams.team_id"),
        nullable=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )

    # Relationships
    calendar_item = relationship("CalendarItem", back_populates="assignments")
    user = relationship("User")
    team = relationship("Team")

    # Partial unique indexes for preventing duplicates
    sa.Index(
        "ix_calendar_item_user_assignment_unique",
        calendar_item_id,
        user_id,
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    sa.Index(
        "ix_calendar_item_team_assignment_unique",
        calendar_item_id,
        team_id,
        unique=True,
        postgresql_where=sa.text("team_id IS NOT NULL"),
    )

    __table_args__ = (
        # Ensure an assignee exists (user or team). Rows should represent
        # exactly one assignee type.
        sa.CheckConstraint(
            "(user_id IS NOT NULL) <> (team_id IS NOT NULL)",
            name="chk_calendar_item_assignment_exactly_one_assignee",
        ),
        {"schema": "operational"},
    )


class CalendarItemCategory(Base):
    __tablename__ = "calendar_item_categories"
    __table_args__ = {"schema": "operational"}

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    short_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    long_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    color_code: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


class ProjectDataLastUpdated(Base):
    __tablename__ = "project_data_last_updated"

    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
        primary_key=True,
    )
    time_error: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True),
    )
    time_empty: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True),
    )
    time_last: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime(timezone=True))

    __table_args__ = {"schema": "operational"}


class ProjectType(Base):
    __tablename__ = "project_types"

    project_type_id: Mapped[enumerations.ProjectTypeEnum] = mapped_column(
        sa.SmallInteger,
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "operational"}


class Racking(Base):
    __tablename__ = "rackings"

    # Admin
    racking_id: Mapped[int] = mapped_column(
        sa.SmallInteger,
        primary_key=True,
        autoincrement=False,
    )
    racking_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.racking_types.racking_type_id"),
    )
    manufacturer: Mapped[str]
    model: Mapped[str] = mapped_column(unique=True)
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
        primary_key=True,
        server_default="01959294-3e51-4d3e-9f57-e9c2c3635c84",
    )
    device_model_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.device_models.device_model_id"),
    )

    # Specifications
    max_rotation_angle: Mapped[float] = mapped_column(comment="Degrees")
    min_rotation_angle: Mapped[float] = mapped_column(comment="Degrees")
    wind_stow_angle: Mapped[float] = mapped_column(comment="Degrees")
    wind_stow_threshold: Mapped[float] = mapped_column(comment="Meters per Second")
    hail_stow_angle: Mapped[float] = mapped_column(comment="Degrees")
    snow_stow_angle: Mapped[float] = mapped_column(comment="Degrees")

    # Performance Modeling
    module_orientation: Mapped[enumerations.RackingArchitecture] = mapped_column(
        sa.SmallInteger,
        server_default=str(enumerations.RackingArchitecture.PORTRAIT),
        comment="Orientation of module on the rack, either portrait or landscape",
    )
    num_modules_in_orientation: Mapped[int] = mapped_column(
        server_default="1", comment="Number of modules in the given orientation"
    )
    pile_height: Mapped[float] = mapped_column(server_default="1.6")
    structure_shading_factor: Mapped[float] = mapped_column(server_default="0.05")
    rear_mismatch_factor: Mapped[float] = mapped_column(server_default="0.10")

    __table_args__ = (
        sa.UniqueConstraint("manufacturer", "model", "company_id"),
        {"schema": "operational"},
    )


class RackingType(Base):
    __tablename__ = "racking_types"

    racking_type_id: Mapped[int] = mapped_column(
        sa.SmallInteger,
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "operational"}


class ReportInstance(Base):
    __tablename__ = "report_instances"

    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
        primary_key=True,
    )
    report_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.report_types.report_type_id"),
        primary_key=True,
    )
    is_visible: Mapped[bool] = mapped_column(server_default="FALSE")

    report_type = relationship("ReportType")

    __table_args__ = {"schema": "operational"}


class ReportType(Base):
    __tablename__ = "report_types"

    report_type_id: Mapped[int] = mapped_column(
        sa.SmallInteger,
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str] = mapped_column(unique=True)
    doc_url: Mapped[str | None]
    description: Mapped[str | None]

    __table_args__ = {"schema": "operational"}


class RootCause(Base):
    __tablename__ = "root_causes"

    root_cause_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    device_type_id: Mapped[int] = mapped_column(
        sa.SmallInteger,
        sa.ForeignKey("operational.device_types.device_type_id"),
    )
    name_short: Mapped[str]
    name_long: Mapped[str]

    __table_args__ = {"schema": "operational"}


class SensorType(Base):
    __tablename__ = "sensor_types"

    sensor_type_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    device_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.device_types.device_type_id"),
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]
    name_metric: Mapped[str]
    unit: Mapped[str | None]
    description: Mapped[str | None]

    __table_args__ = {"schema": "operational"}

    def __str__(self):
        """Return the human-readable sensor type name."""
        return self.name_long


class UserProjectLabel(Base):
    __tablename__ = "user_project_labels"

    user_project_label_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(sa.String(64))
    color: Mapped[str] = mapped_column(sa.String(7), server_default="#adb5bd")
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "user_id",
            "name",
            name="uq_user_project_labels_user_id_name",
        ),
        {"schema": "operational"},
    )


class ProjectLabel(Base):
    __tablename__ = "project_labels"

    user_project_label_id: Mapped[int] = mapped_column(
        sa.ForeignKey(
            "operational.user_project_labels.user_project_label_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey(
            "operational.projects.project_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    __table_args__ = {"schema": "operational"}


class CECPVInverter(Base):
    __tablename__ = "cec_pv_inverters"

    cec_pv_inverter_id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str]
    model_number: Mapped[str]
    hybrid_inverter: Mapped[bool | None]
    ul1741sb_certification: Mapped[bool | None]
    ul1741sa_testing: Mapped[bool | None]
    ul1741sa_13_volt_var: Mapped[bool | None]
    ul1741sa_freq_watt_volt_watt: Mapped[bool | None]
    ul1741sa_disable_permit_service: Mapped[bool | None]
    common_smart_inverter_profile: Mapped[bool | None]
    monitor_key_data_scheduling: Mapped[bool | None]
    description: Mapped[str | None]
    max_output_power_unity_pf: Mapped[float | None]
    nominal_voltage: Mapped[float | None]
    weighted_efficiency: Mapped[float | None]
    ul1741sb_certification_3rd_ed_entity: Mapped[str | None]
    ul1741sb_certification_3rd_ed_date: Mapped[sa.Date | None] = mapped_column(
        sa.Date(),
    )
    ul1741sa_certification_sa8_sa13_entity: Mapped[str | None]
    ul1741sa_certification_sa8_sa13_date: Mapped[sa.Date | None] = mapped_column(
        sa.Date(),
    )
    ul1741sa_certification_sa8_sa13_firmware_versions: Mapped[str | None]
    ul1741sa_13_volt_var_date: Mapped[sa.Date | None] = mapped_column(sa.Date())
    ul1741sa_freq_watt_volt_watt_date: Mapped[sa.Date | None] = mapped_column(
        sa.Date(),
        nullable=True,
    )
    ul1741sa_disable_permit_service_date: Mapped[sa.Date | None] = mapped_column(
        sa.Date(),
    )
    inverter_csip_conformance_entity: Mapped[str | None]
    inverter_csip_conformance_date: Mapped[sa.Date | None] = mapped_column(sa.Date())
    monitor_key_data_scheduling_att: Mapped[str | None]
    notes: Mapped[str | None]
    built_in_meter: Mapped[bool | None]
    microinverter: Mapped[bool | None]
    night_tare_loss: Mapped[float | None]
    power_rating_40_deg_c: Mapped[float | None]
    night_tare_loss_40_deg_c: Mapped[float | None]
    voltage_minimum: Mapped[float | None]
    voltage_nominal: Mapped[float | None]
    voltage_maximum: Mapped[float | None]
    power_level_10: Mapped[float | None]
    power_level_20: Mapped[float | None]
    power_level_30: Mapped[float | None]
    power_level_50: Mapped[float | None]
    power_level_75: Mapped[float | None]
    power_level_100: Mapped[float | None]
    efficiency_vmin_10: Mapped[float | None]
    efficiency_vmin_20: Mapped[float | None]
    efficiency_vmin_30: Mapped[float | None]
    efficiency_vmin_50: Mapped[float | None]
    efficiency_vmin_75: Mapped[float | None]
    efficiency_vmin_100: Mapped[float | None]
    efficiency_vmin_wtd: Mapped[float | None]
    efficiency_vnom_10: Mapped[float | None]
    efficiency_vnom_20: Mapped[float | None]
    efficiency_vnom_30: Mapped[float | None]
    efficiency_vnom_50: Mapped[float | None]
    efficiency_vnom_75: Mapped[float | None]
    efficiency_vnom_100: Mapped[float | None]
    efficiency_vnom_wtd: Mapped[float | None]
    efficiency_vmax_10: Mapped[float | None]
    efficiency_vmax_20: Mapped[float | None]
    efficiency_vmax_30: Mapped[float | None]
    efficiency_vmax_50: Mapped[float | None]
    efficiency_vmax_75: Mapped[float | None]
    efficiency_vmax_100: Mapped[float | None]
    efficiency_vmax_wtd: Mapped[float | None]
    grid_support_listing_date: Mapped[sa.Date | None] = mapped_column(sa.Date())
    last_update: Mapped[sa.Date | None] = mapped_column(sa.Date())

    __table_args__ = (
        sa.UniqueConstraint("manufacturer", "model_number"),
        {"schema": "operational"},
    )


class PVModule(Base):
    __tablename__ = "pv_modules"

    pv_module_id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("admin.companies.company_id"),
        server_default="01959294-3e51-4d3e-9f57-e9c2c3635c84",
    )
    device_model_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.device_models.device_model_id"),
    )
    manufacturer: Mapped[str]
    model: Mapped[str]
    family: Mapped[str | None]
    technology: Mapped[str]
    bifaciality_factor: Mapped[float] = mapped_column(server_default="0.0")
    pmax: Mapped[float]
    isc: Mapped[float]
    voc: Mapped[float]
    imp: Mapped[float]
    vmp: Mapped[float]
    gamma_pmax: Mapped[float]
    alpha_isc: Mapped[float]
    beta_voc: Mapped[float]
    warranted_degradation_rate: Mapped[float]
    warranted_degradation_initial: Mapped[float]
    length: Mapped[float] = mapped_column(server_default="2.0")
    width: Mapped[float] = mapped_column(server_default="1.0")
    frame_overhang: Mapped[float] = mapped_column(server_default="0.0")
    has_ar_coating: Mapped[bool] = mapped_column(server_default="false")
    half_cut: Mapped[bool] = mapped_column(server_default="true")
    cells_in_series: Mapped[int] = mapped_column(sa.SmallInteger, server_default="72")
    cells_in_parallel: Mapped[int] = mapped_column(sa.SmallInteger, server_default="1")
    photocurrent: Mapped[float | None]
    diode_saturation_current: Mapped[float | None]
    r_series: Mapped[float | None]
    r_shunt: Mapped[float | None]
    r_shunt_0: Mapped[float | None]
    r_shunt_exponent: Mapped[float | None]
    diode_ideality_factor: Mapped[float | None]
    diode_ideality_factor_temp_coefficient: Mapped[float | None]
    modified_ideality_factor: Mapped[float | None]
    eg: Mapped[float | None]
    degdt: Mapped[float | None]
    data_source: Mapped[str | None] = mapped_column(sa.Text, server_default="CEC")

    __table_args__ = (
        sa.UniqueConstraint("manufacturer", "model", "company_id"),
        {"schema": "operational"},
    )


class CECPVModule(Base):
    __tablename__ = "cec_pv_modules"

    cec_pv_module_id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str]
    model_number: Mapped[str]
    description: Mapped[str | None]
    safety_certification: Mapped[str | None]
    nameplate_pmax: Mapped[float | None]
    ptc: Mapped[float | None]
    notes: Mapped[str | None]
    design_qualification: Mapped[sa.Date | None] = mapped_column(sa.Date())
    performance_evaluation: Mapped[str | None]
    family: Mapped[str | None]
    technology: Mapped[str | None]
    a_c: Mapped[float | None]
    n_s: Mapped[int | None]
    n_p: Mapped[int | None]
    bipv: Mapped[bool | None]
    nameplate_isc: Mapped[float | None]
    nameplate_voc: Mapped[float | None]
    nameplate_ipmax: Mapped[float | None]
    nameplate_vpmax: Mapped[float | None]
    average_noct: Mapped[float | None]
    gamma_pmax: Mapped[float | None]
    alpha_isc: Mapped[float | None]
    beta_voc: Mapped[float | None]
    alpha_ipmax: Mapped[float | None]
    beta_vpmax: Mapped[float | None]
    ipmax_low: Mapped[float | None]
    vpmax_low: Mapped[float | None]
    ipmax_noct: Mapped[float | None]
    vpmax_noct: Mapped[float | None]
    mounting: Mapped[str | None]
    type: Mapped[str | None]
    short_side: Mapped[float | None]
    long_side: Mapped[float | None]
    geometric_multiplier: Mapped[float | None]
    p2p_ref: Mapped[float | None]
    cec_listing_date: Mapped[sa.Date | None] = mapped_column(sa.Date())
    last_update: Mapped[sa.Date | None] = mapped_column(sa.Date())

    __table_args__ = (
        sa.UniqueConstraint("manufacturer", "model_number"),
        {"schema": "operational"},
    )


class Inverter(Base):
    __tablename__ = "inverters"

    # General inverter parameters
    inverter_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    manufacturer: Mapped[str]
    model: Mapped[str]
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
        primary_key=True,
        server_default="01959294-3e51-4d3e-9f57-e9c2c3635c84",
    )
    device_model_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.device_models.device_model_id"),
    )

    # Operating window parameters
    voltage_mpp_min: Mapped[float]  # MPP search lower limit
    voltage_mpp_max: Mapped[float]  # MPP search upper limit
    voltage_start_up: Mapped[float]  # Array must hit this to start up in the morning
    voltage_min: Mapped[float]  # Array must be at least this amount
    voltage_max: Mapped[float]  # Maximum operational voltage, generally 1500V
    current_max: Mapped[float]  # Maximum operational current

    # Temperature-dependent power characteristics
    power_max_at_reference_temp: Mapped[list[float]] = mapped_column(sa.ARRAY(sa.Float))
    reference_temp: Mapped[list[float]] = mapped_column(sa.ARRAY(sa.Float))

    # Efficiency parameters for reference
    voltage_nominal_efficiency: Mapped[list[float]] = mapped_column(sa.ARRAY(sa.Float))
    efficiency_at_low_voltage: Mapped[list[list[float]]] = mapped_column(
        sa.ARRAY(sa.Float, dimensions=2)
    )
    efficiency_at_mid_voltage: Mapped[list[list[float]]] = mapped_column(
        sa.ARRAY(sa.Float, dimensions=2)
    )
    efficiency_at_high_voltage: Mapped[list[list[float]]] = mapped_column(
        sa.ARRAY(sa.Float, dimensions=2)
    )

    # Inverter efficiency parameters
    power_start_up: Mapped[float] = mapped_column(comment="[W]")
    power_ac_nominal: Mapped[float] = mapped_column(comment="[W]")
    power_dc_nominal: Mapped[float] = mapped_column(comment="[W]")
    voltage_dc_nominal: Mapped[float] = mapped_column(comment="[V]")
    c0: Mapped[float] = mapped_column(comment="[unitless]")
    c1: Mapped[float] = mapped_column(comment="[unitless]")
    c2: Mapped[float] = mapped_column(comment="[unitless]")
    c3: Mapped[float] = mapped_column(comment="[unitless]")
    night_tare: Mapped[float] = mapped_column(comment="[W]")

    # AC side parameters
    voltage_ac_nominal: Mapped[float | None] = mapped_column(comment="[V]")

    __table_args__ = (
        sa.UniqueConstraint("manufacturer", "model", "company_id"),
        sa.CheckConstraint(
            "array_length(power_max_at_reference_temp, 1) = "
            "array_length(reference_temp, 1)",
            name="check_power_temp_arrays_length",
        ),
        sa.CheckConstraint(
            sa.func.array_ndims(efficiency_at_low_voltage) == 2,
            name="check_efficiency_at_low_voltage_ndims",
        ),
        sa.CheckConstraint(
            sa.func.array_ndims(efficiency_at_mid_voltage) == 2,
            name="check_efficiency_at_mid_voltage_ndims",
        ),
        sa.CheckConstraint(
            sa.func.array_ndims(efficiency_at_high_voltage) == 2,
            name="check_efficiency_at_high_voltage_ndims",
        ),
        {"schema": "operational"},
    )


class Transformer(Base):
    __tablename__ = "transformers"

    # general transformer parameters
    transformer_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    manufacturer: Mapped[str]
    model: Mapped[str]

    # Efficiency parameters
    no_load_loss: Mapped[float]  # load loss between 0 and 1.0
    load_loss: Mapped[float]  # no load loss between 0 and 1.0
    rating: Mapped[float]  # nominal power in [W]

    __table_args__ = (
        sa.UniqueConstraint("manufacturer", "model"),
        {"schema": "operational"},
    )


class BESSString(Base):
    """BESS string equipment specifications."""

    __tablename__ = "bess_strings"

    bess_string_id: Mapped[int] = mapped_column(
        primary_key=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
        primary_key=True,
        server_default="01959294-3e51-4d3e-9f57-e9c2c3635c84",
    )
    device_model_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.device_models.device_model_id"),
    )

    configuration: Mapped[str | None]
    chemistry: Mapped[str | None]
    cells_in_series: Mapped[int | None]
    strings_in_parallel: Mapped[int | None]
    module_count: Mapped[int | None]

    nominal_energy_kwh: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    nominal_power_kw: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    charge_power_max_kw: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    discharge_power_max_kw: Mapped[float | None] = mapped_column(sa.Float)
    operating_voltage_min_v: Mapped[float | None] = mapped_column(sa.Float)
    operating_voltage_max_v: Mapped[float | None] = mapped_column(sa.Float)

    dimensions_width_mm: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    dimensions_depth_mm: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    dimensions_height_mm: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    weight_kg: Mapped[float | None] = mapped_column(
        sa.Float,
    )

    bms_supply_voltage_vdc: Mapped[float | None] = mapped_column(sa.Float)
    bms_cell_voltage_accuracy_mv: Mapped[dict | None] = mapped_column(JSONB)
    bms_total_voltage_accuracy_pct: Mapped[float | None] = mapped_column(sa.Float)
    bms_total_voltage_detection_min_v: Mapped[float | None] = mapped_column(sa.Float)
    bms_total_voltage_detection_max_v: Mapped[float | None] = mapped_column(sa.Float)
    bms_current_accuracy_pct: Mapped[float | None] = mapped_column(sa.Float)
    bms_current_min_a: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    bms_current_max_a: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    bms_temperature_accuracy_c: Mapped[dict | None] = mapped_column(JSONB)
    bms_soc_accuracy_pct: Mapped[float | None] = mapped_column(sa.Float)
    bms_soc_accuracy_notes: Mapped[str | None]

    enclosure_rating_battery: Mapped[str | None]
    enclosure_rating_electrical: Mapped[str | None]
    anti_corrosion_rating: Mapped[str | None]

    operating_temp_min_c: Mapped[float | None] = mapped_column(sa.Float)
    operating_temp_max_c: Mapped[float | None] = mapped_column(sa.Float)
    storage_temp_min_c: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    storage_temp_max_c: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    relative_humidity_min_pct: Mapped[float | None] = mapped_column(sa.Float)
    relative_humidity_max_pct: Mapped[float | None] = mapped_column(sa.Float)
    altitude_max_m: Mapped[float | None] = mapped_column(sa.Float)

    thermal_management_method: Mapped[str | None]
    auxiliary_power_phase: Mapped[str | None]
    auxiliary_power_ac_min_v: Mapped[float | None] = mapped_column(sa.Float)
    auxiliary_power_ac_max_v: Mapped[float | None] = mapped_column(sa.Float)
    auxiliary_power_frequency_hz: Mapped[dict | None] = mapped_column(JSONB)

    charge_power_limit_map: Mapped[dict | None] = mapped_column(JSONB)
    discharge_power_limit_map: Mapped[dict | None] = mapped_column(JSONB)
    standards: Mapped[dict | None] = mapped_column(JSONB)

    source_filename: Mapped[str | None]
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        onupdate=sa.func.now(),
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint("device_model_id", "company_id"),
        {"schema": "operational"},
    )


class BESSPCS(Base):
    """BESS PCS equipment specifications."""

    __tablename__ = "bess_pcss"

    bess_pcs_id: Mapped[int] = mapped_column(
        primary_key=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
        primary_key=True,
        server_default="01959294-3e51-4d3e-9f57-e9c2c3635c84",
    )
    device_model_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.device_models.device_model_id"),
    )

    # DC-side
    dc_voltage_min_v: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    dc_voltage_max_v: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    battery_voltage_min_v: Mapped[float | None] = mapped_column(sa.Float)
    battery_voltage_max_v: Mapped[float | None] = mapped_column(sa.Float)
    dc_current_max_a: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    dc_current_per_input_a: Mapped[float | None] = mapped_column(sa.Float)
    num_dc_inputs: Mapped[int | None]
    dc_input_topology: Mapped[str | None]

    # AC-side
    ac_power_nominal_kw: Mapped[float | None] = mapped_column(sa.Float)
    ac_power_max_kw: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    ac_voltage_nominal_v: Mapped[float | None] = mapped_column(sa.Float)
    ac_voltage_min_v: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    ac_voltage_max_v: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    ac_current_max_a: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    grid_frequency_nominal_hz: Mapped[float | None] = mapped_column(sa.Float)
    power_factor_min: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    power_factor_max: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    thdi_pct: Mapped[float | None] = mapped_column(
        sa.Float,
    )

    # Bidirectional / storage
    bidirectional: Mapped[bool | None]
    charge_power_max_kw: Mapped[float | None] = mapped_column(sa.Float)
    discharge_power_max_kw: Mapped[float | None] = mapped_column(sa.Float)
    four_quadrant_operation: Mapped[bool | None]
    black_start_capability: Mapped[bool | None]
    grid_forming_capable: Mapped[bool | None]
    grid_following_capable: Mapped[bool | None]
    response_time_ms: Mapped[float | None] = mapped_column(
        sa.Float,
    )

    # Off-grid / microgrid
    offgrid_supported: Mapped[bool | None]
    offgrid_voltage_nominal_v: Mapped[float | None] = mapped_column(sa.Float)
    offgrid_voltage_min_v: Mapped[float | None] = mapped_column(sa.Float)
    offgrid_voltage_max_v: Mapped[float | None] = mapped_column(sa.Float)
    offgrid_voltage_distortion_pct: Mapped[float | None] = mapped_column(sa.Float)
    dc_injection_limit_pct: Mapped[float | None] = mapped_column(sa.Float)
    unbalanced_load_capacity_pct: Mapped[float | None] = mapped_column(sa.Float)

    # Efficiency
    efficiency_max_pct: Mapped[float | None] = mapped_column(sa.Float)
    efficiency_cec_pct: Mapped[float | None] = mapped_column(sa.Float)
    efficiency_european_pct: Mapped[float | None] = mapped_column(sa.Float)

    # Transformer
    transformer_integrated: Mapped[bool | None]
    transformer_power_rating_kva: Mapped[float | None] = mapped_column(sa.Float)
    transformer_lv_voltage_kv: Mapped[float | None] = mapped_column(sa.Float)
    transformer_mv_voltage_kv: Mapped[float | None] = mapped_column(sa.Float)
    transformer_vector_group: Mapped[str | None]
    transformer_cooling_type: Mapped[str | None]
    transformer_insulation_type: Mapped[str | None]

    # Environmental / mechanical
    ip_rating: Mapped[str | None]
    operating_temp_min_c: Mapped[float | None] = mapped_column(sa.Float)
    operating_temp_max_c: Mapped[float | None] = mapped_column(sa.Float)
    relative_humidity_max_pct: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    altitude_max_m: Mapped[float | None] = mapped_column(
        sa.Float,
    )
    cooling_method: Mapped[str | None]
    dimensions_width_mm: Mapped[float | None] = mapped_column(sa.Float)
    dimensions_depth_mm: Mapped[float | None] = mapped_column(sa.Float)
    dimensions_height_mm: Mapped[float | None] = mapped_column(sa.Float)
    weight_kg: Mapped[float | None] = mapped_column(
        sa.Float,
    )

    # Communications / controls
    communication_protocols: Mapped[list[str] | None] = mapped_column(
        sa.ARRAY(sa.String)
    )
    supports_ieee_2030_5: Mapped[bool | None]
    supports_scada: Mapped[bool | None]
    ems_interface: Mapped[bool | None]

    # System architecture / features
    modular: Mapped[bool | None]
    module_power_rating_kw: Mapped[float | None] = mapped_column(sa.Float)
    max_system_power_kw: Mapped[float | None] = mapped_column(sa.Float)
    containerized: Mapped[bool | None]
    mv_station_integrated: Mapped[bool | None]
    battery_cluster_expansion: Mapped[bool | None]
    soc_balancing_support: Mapped[bool | None]

    source_filename: Mapped[str | None]
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        onupdate=sa.func.now(),
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint("device_model_id", "company_id"),
        {"schema": "operational"},
    )


class CMMSProvider(Base):
    __tablename__ = "cmms_providers"

    cmms_provider_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]

    __table_args__ = {"schema": "operational"}


class ForecastWeatherProvider(Base):
    __tablename__ = "forecast_weather_providers"

    forecast_weather_provider_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]
    is_public: Mapped[bool] = mapped_column(server_default="FALSE")

    models = relationship(
        "ForecastWeatherModel", back_populates="forecast_weather_provider"
    )

    __table_args__ = {"schema": "operational"}


class ForecastWeatherModel(Base):
    __tablename__ = "forecast_weather_models"

    forecast_weather_model_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=False,
    )
    forecast_weather_provider_id: Mapped[int] = mapped_column(
        sa.ForeignKey(
            "operational.forecast_weather_providers.forecast_weather_provider_id"
        )
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]

    forecast_weather_provider = relationship(
        "ForecastWeatherProvider", back_populates="models"
    )

    __table_args__ = {"schema": "operational"}


class CMMSIntegration(Base):
    __tablename__ = "cmms_integrations"

    cmms_integration_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
    )
    cmms_provider_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.cmms_providers.cmms_provider_id"),
    )
    project_name: Mapped[str | None]
    domain_name: Mapped[str | None]

    project = relationship("Project")

    cmms_provider = relationship("CMMSProvider")

    __table_args__ = {"schema": "operational"}


class CMMSPermission(Base):
    __tablename__ = "cmms_permissions"

    cmms_integration_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.cmms_integrations.cmms_integration_id"),
        primary_key=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
        primary_key=True,
    )
    can_view: Mapped[bool] = mapped_column(server_default="FALSE")

    cmms_integration = relationship("CMMSIntegration")

    __table_args__ = {"schema": "operational"}


class DroneProvider(Base):
    __tablename__ = "drone_providers"

    drone_provider_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=False
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]

    __table_args__ = {"schema": "operational"}


class DroneIntegration(Base):
    __tablename__ = "drone_integrations"

    drone_integration_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id"),
    )
    drone_provider_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.drone_providers.drone_provider_id"),
    )
    provider_project_id: Mapped[str]

    drone_provider = relationship("DroneProvider")

    __table_args__ = {"schema": "operational"}


class DronePermission(Base):
    __tablename__ = "drone_permissions"

    drone_integration_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.drone_integrations.drone_integration_id"),
        primary_key=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"),
        primary_key=True,
    )
    can_view: Mapped[bool] = mapped_column(server_default="FALSE")

    drone_integration = relationship("DroneIntegration")

    __table_args__ = {"schema": "operational"}


class CustomDashboard(Base):
    __tablename__ = "custom_dashboards"
    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("operational.projects.project_id"),
    )
    dashboard_name: Mapped[str] = mapped_column(sa.Text)
    owner_user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
    )
    default_time_range: Mapped[enumerations.DefaultTimeRange] = mapped_column(
        sa.Integer
    )
    default_kpi_time_range: Mapped[enumerations.DefaultKPITimeRange] = mapped_column(
        sa.Integer
    )
    components: Mapped[dict] = mapped_column(
        JSONB
    )  # { {"component_id": int, "x": int, "y": int, "w": int, "h": int } []}
    __table_args__ = {"schema": "operational"}


class CustomDashboardComponent(Base):
    __tablename__ = "custom_dashboard_components"
    component_id: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )
    component_type: Mapped[enumerations.ComponentType] = mapped_column(sa.Integer)
    config: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = {"schema": "operational"}


class CustomDashboardShare(Base):
    __tablename__ = "custom_dashboard_shares"

    share_id: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )
    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("operational.custom_dashboards.dashboard_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("admin.users.user_id"),
        index=True,
        nullable=False,
    )

    __table_args__ = (
        sa.UniqueConstraint("dashboard_id", "user_id"),
        {"schema": "operational"},
    )


class PVBudgetedSeries(Base):
    __tablename__ = "pv_budgeted_series"

    pv_budgeted_series_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("admin.companies.company_id"), index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("operational.projects.project_id"), index=True
    )
    p_value: Mapped[str] = mapped_column(comment="P-value (e.g., p50, p90)")
    frequency: Mapped[str] = mapped_column(comment="Data frequency (e.g., hourly)")
    soiling_mode: Mapped[enumerations.PVBudgetedSoilingMode | None] = mapped_column(
        comment="Soiling calculation mode"
    )
    soiling_fixed_percentage: Mapped[float | None] = mapped_column(
        comment="Fixed soiling percentage when mode is fixed"
    )
    tmy_source: Mapped[str | None] = mapped_column(
        comment="TMY data source (e.g., TMY NSRDB 2020)"
    )
    model_version: Mapped[str | None] = mapped_column(
        comment="PV model version (e.g., PVSyst 7.4.7)"
    )
    filename: Mapped[str | None] = mapped_column(
        comment="Source filename (e.g., DBD_VDU_res0.xlsx)"
    )

    # Relationship to data points
    data_points = relationship("PVBudgetedData", back_populates="series")

    __table_args__ = {"schema": "operational"}


class PVBudgetedData(Base):
    __tablename__ = "pv_budgeted_data"

    pv_budgeted_series_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.pv_budgeted_series.pv_budgeted_series_id"),
        primary_key=True,
    )
    time: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), primary_key=True
    )
    poi_ac_power: Mapped[float] = mapped_column(
        comment="Point of Interconnection AC Power [MW]"
    )
    ghi: Mapped[float | None] = mapped_column(
        comment="Global Horizontal Irradiance [W/m²]"
    )
    poa: Mapped[float] = mapped_column(comment="Plane of Array Irradiance [W/m²]")
    temperature: Mapped[float | None] = mapped_column(comment="Temperature [°C]")
    soiling_percentage: Mapped[float | None] = mapped_column(
        comment="Soiling loss as percentage [%]"
    )

    # Relationship to series
    series = relationship("PVBudgetedSeries", back_populates="data_points")

    __table_args__ = {"schema": "operational"}


class QSEProvider(Base):
    __tablename__ = "qse_providers"

    qse_provider_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str]

    __table_args__ = {"schema": "operational"}


class QSEIntegration(Base):
    __tablename__ = "qse_integrations"

    qse_integration_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("operational.projects.project_id")
    )
    qse_provider_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.qse_providers.qse_provider_id")
    )
    qse_project_identifier: Mapped[str]
    provider_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    qse_provider = relationship("QSEProvider")

    project = relationship("Project")

    __table_args__ = {"schema": "operational"}


class QSEPermission(Base):
    __tablename__ = "qse_permissions"

    qse_integration_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.qse_integrations.qse_integration_id"),
        primary_key=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("admin.companies.company_id"), primary_key=True
    )
    can_view: Mapped[bool] = mapped_column(server_default="FALSE")

    qse_integration = relationship("QSEIntegration")

    __table_args__ = {"schema": "operational"}


class QSEField(Base):
    __tablename__ = "qse_fields"

    qse_provider_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.qse_providers.qse_provider_id"), primary_key=True
    )
    qse_field_name: Mapped[str] = mapped_column(primary_key=True)
    name_short: Mapped[str]
    name_long: Mapped[str]
    description: Mapped[str]
    unit: Mapped[str]
    unit_offset: Mapped[float | None] = mapped_column(sa.Double)
    unit_scale: Mapped[float | None] = mapped_column(sa.Double)

    qse_provider = relationship("QSEProvider")

    __table_args__ = {"schema": "operational"}


class ActiveEvent(Base):
    __tablename__ = "active_events"

    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey(
            "operational.projects.project_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    event_id: Mapped[int] = mapped_column(
        sa.Integer,
        primary_key=True,
    )
    device_id: Mapped[int]
    device_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.device_types.device_type_id"),
    )
    device_name_full: Mapped[str]
    failure_mode_id: Mapped[int] = mapped_column(
        sa.ForeignKey("operational.failure_modes.failure_mode_id"),
    )
    root_cause_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("operational.root_causes.root_cause_id"),
    )
    time_start: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))
    loss_total_financial: Mapped[float | None] = mapped_column(sa.Double)
    loss_total_energetic: Mapped[float | None] = mapped_column(sa.Double)

    device_type = relationship("DeviceType")
    failure_mode = relationship("FailureMode")
    root_cause = relationship("RootCause")

    __table_args__ = {"schema": "operational"}


##### END OPERATIONAL SCHEMA #####
