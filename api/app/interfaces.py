"""
The interface.py module is used to serialize and validate data which is being
accepted or returned by the API.

Each interface in this top file is the "get" level interface which should return
all of the fields from the database.

If you have an interface which only uses a subset of the "get" level interface,
you should create a child interface in the corresponding _crud file.
"""

import datetime
import uuid
from typing import Annotated, Any, cast

from core.enumerations import NotificationSeverity, UserTypeEnum
from geoalchemy2.shape import to_shape
from pydantic import BaseModel, Field, conlist, model_validator
from pydantic.config import ConfigDict
from shapely import wkb, wkt
from shapely.geometry import mapping


class APIKey(BaseModel):
    """Apikey model."""

    api_key: str | None


class User(BaseModel):
    """User model."""

    user_id: str
    user_type_id: UserTypeEnum
    company_id: uuid.UUID
    name_long: str
    api_key: str | None


class UserCreate(BaseModel):
    """Usercreate model."""

    first_name: str
    last_name: str
    email: str
    company_id: uuid.UUID
    company_name_short: str


class UserType(BaseModel):
    """Usertype model."""

    user_type_id: UserTypeEnum
    name_short: str


class UserWithPermissions(BaseModel):
    """Userwithpermissions model."""

    user_id: str
    name_long: str
    permission_ids: list[int]


class UserWithProjects(BaseModel):
    """Userwithprojects model."""

    user_id: str
    user_type_id: UserTypeEnum
    company_id: uuid.UUID
    name_long: str
    operational_project_ids: list[uuid.UUID]
    image_url: str | None = None


class UserData(BaseModel):
    """Userdata model."""

    user_id: str
    company_id: uuid.UUID
    public_metadata: dict
    api_key: str | None
    operational_project_ids: list[uuid.UUID]
    user_type_id: UserTypeEnum


class UserAuthed(BaseModel):
    """Userauthed model."""

    user_id: str
    company_id: uuid.UUID
    public_metadata: dict
    operational_project_ids: list[uuid.UUID]
    user_type_id: UserTypeEnum
    authentication_method: str


class UserSubscription(BaseModel):
    """Usersubscription model."""

    user_id: str
    operational_project_id: uuid.UUID
    notifications: bool
    reports: bool


class UserSubscriptionUpdate(BaseModel):
    """Usersubscriptionupdate model."""

    subscribe: bool


class Notification(BaseModel):
    """Notification model."""

    notification_id: int
    project_id: uuid.UUID
    notification_type_id: int
    data: dict
    severity: str
    created_at: datetime.datetime
    sent_at: datetime.datetime | None
    state: str | None = None  # Notification state: unread, read, deleted

    model_config = ConfigDict(from_attributes=True)


class NotificationType(BaseModel):
    """Notification type model."""

    model_config = {"from_attributes": True}

    notification_type_id: int
    name_long: str
    in_app_enabled_default: bool
    email_enabled_default: bool
    in_app_severity_default: NotificationSeverity | None = None
    email_severity_default: NotificationSeverity | None = None


class NotificationPreference(BaseModel):
    """Notification preference model."""

    model_config = {"from_attributes": True}

    notification_preference_id: int
    user_id: str
    project_id: uuid.UUID
    notification_type_id: int
    in_app_enabled: bool
    email_enabled: bool
    in_app_min_severity: NotificationSeverity
    email_min_severity: NotificationSeverity


class NotificationPreferenceUpdate(BaseModel):
    """Notification preference update model."""

    project_id: uuid.UUID
    notification_type_id: int
    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
    in_app_min_severity: NotificationSeverity | None = None
    email_min_severity: NotificationSeverity | None = None


class UserProjectFavoriteUpdate(BaseModel):
    """Userprojectfavoriteupdate model."""

    is_favorited: bool


class UserKPITypes(BaseModel):
    """Userkpitypes model."""

    user_id: str
    kpi_type_id: int
    is_favorited: bool


class UserKPITypeFavoriteUpdate(BaseModel):
    """User KPI type favorite update model."""

    kpi_type_id: int
    is_favorited: bool


class Permission(BaseModel):
    """Permission model."""

    permission_id: int
    name_short: str
    name_long: str


class UserPermission(BaseModel):
    """Userpermission model."""

    user_id: str
    project_id: uuid.UUID
    permission_id: int


# The Point and Polygon models below represent standard GeoJSON. This
# function (along with the model_validator) converts the GeoAlchemy2
# WKBElements to GeoJSON. The pydantic models then validate the GeoJSON.


def convert(*, WKBElement: Any) -> dict[str, Any] | None:
    """Handle convert.

    Args:
        WKBElement: GeoAlchemy WKBElement, GeoJSON dict, WKB bytes, or
            WKT string to convert.
    """
    if WKBElement is None:
        return None
    # If it's already a dict (GeoJSON), return as-is
    if isinstance(WKBElement, dict):
        return cast(dict[str, Any], WKBElement)
    # If it's raw WKB bytes (e.g. from Polars/Pandas via db_query), parse with shapely
    if isinstance(WKBElement, bytes):
        return cast(dict[str, Any], mapping(wkb.loads(WKBElement)))
    # If it's WKT string (unlikely but possible), parse with shapely
    if isinstance(WKBElement, str):
        return cast(dict[str, Any], mapping(wkt.loads(WKBElement)))
    # Only convert WKBElement objects from the database
    return cast(dict[str, Any], mapping(to_shape(WKBElement)))


class Point(BaseModel):
    """Point model."""

    type: str
    coordinates: conlist(float, min_length=2, max_length=2)  # type: ignore # pyright: ignore

    @model_validator(mode="before")  # nosemgrep: python-enforce-keyword-only-args
    @staticmethod
    def convert_point(
        point: Any,
    ) -> dict | None:  # nosemgrep: python-enforce-keyword-only-args
        """Handle convert point.

        Args:
            point: GeoAlchemy WKBElement, GeoJSON dict, or WKT/WKB input.
        """
        return convert(WKBElement=point)


class Polygon(BaseModel):
    """Polygon model."""

    type: str
    # TODO: Generate more specific validation for POLYGON or MULTIPOLYGON
    coordinates: list[Any]

    @model_validator(mode="before")  # nosemgrep: python-enforce-keyword-only-args
    @staticmethod
    def convert_polygon(
        polygon: Any,
    ) -> dict | None:  # nosemgrep: python-enforce-keyword-only-args
        """Handle convert polygon.

        Args:
            polygon: GeoAlchemy WKBElement, GeoJSON dict, or WKT/WKB input.
        """
        return convert(WKBElement=polygon)


class MultiPolygon(BaseModel):
    """Multipolygon model."""

    type: str
    coordinates: list[Any]

    @model_validator(mode="before")  # nosemgrep: python-enforce-keyword-only-args
    @staticmethod
    def convert_multipolygon(  # nosemgrep: python-enforce-keyword-only-args
        multipolygon: Any,
    ) -> dict | None:
        """Handle convert multipolygon.

        Args:
            multipolygon: GeoAlchemy WKBElement, GeoJSON dict, or WKT/WKB input.
        """
        return convert(WKBElement=multipolygon)


class ProjectType(BaseModel):
    """Projecttype model."""

    project_type_id: int
    name_short: str
    name_long: str

    model_config = {"from_attributes": True}


class ProjectStatusType(BaseModel):
    """Projectstatustype model."""

    project_status_type_id: int
    name_short: str
    name_long: str

    model_config = {"from_attributes": True}


class ProjectSpec(BaseModel):
    """Projectspec model."""

    used_device_type_ids: list[int] | None = None
    used_sensor_type_ids: list[int] | None = None
    device_types_with_all_points: list[int] | None = None
    device_types_all_with_polygons: list[int] | None = None


# --- Operational.Projects ---
class ProjectShared(BaseModel):
    """
    Shared attributes of the following classes:
    - Project
    - ProjectCreate
    """

    project_type_id: int
    name_long: str
    address: str | None = None
    elevation: float  # meters
    time_zone: str
    poi: Annotated[
        float,
        "The Point of Interconnection limit (LGIA limit) in MW",
    ]
    capacity_dc: Annotated[
        float | None,
        "The PV specific DC capacity of the project in MW",
    ] = None
    capacity_ac: Annotated[
        float | None,
        "The PV specific AC capacity of the project in MW",
    ] = None
    capacity_bess_power_ac: Annotated[
        float | None,
        "The AC specific capacity of the battery energy storage system in MW",
    ] = None
    capacity_bess_energy_bol_dc: Annotated[
        float | None,
        """
        The DC specific capacity of the battery energy storage system
        at beginning of life in MWh
        """,
    ] = None
    ppa: Annotated[
        dict | None,
        "Power Purchase Agreement details, currently only flat rate",
    ] = None
    cod: Annotated[
        datetime.date | None,
        "Commercial Operation Date of the project",
    ] = None


class ProjectCreate(ProjectShared):
    """
    Inherits from ProjectShared.
    Represents the user inputs to create a new project
    """

    latitude: float
    longitude: float


class ProjectUpdate(BaseModel):
    """
    Represents the fields that can be updated for an existing project
    """

    name_long: str | None = None
    address: str | None = None
    elevation: float | None = None
    time_zone: str | None = None
    poi: float | None = None
    capacity_dc: float | None = None
    capacity_ac: float | None = None
    capacity_bess_power_ac: float | None = None
    capacity_bess_energy_bol_dc: float | None = None
    ppa: dict | None = None
    cod: str | None = None
    commencement_of_construction_date: str | None = None
    financial_close_date: str | None = None
    notice_to_proceed_date: str | None = None
    mechanical_completion_date: str | None = None
    substantial_completion_date: str | None = None
    interconnection_approval_date: str | None = None
    performance_test_completion_date: str | None = None
    placed_in_service_date: str | None = None
    first_realtime_data_received_date: str | None = None
    first_data_backfilled_date: str | None = None
    interconnecting_utility: str | None = None
    interconnecting_substation: str | None = None
    interconnecting_voltage: float | None = None
    interconnecting_iso: str | None = None
    interconnecting_node_code: str | None = None
    gsheet_id: str | None = None


class Project(ProjectShared):
    """
    Inherits from ProjectCreate.

    The full project details, basically the entire row from the database.
    """

    # --- active columns ---
    # Project metadata
    project_id: uuid.UUID
    name_short: str
    data_table: str = "data_timeseries"
    data_interval: str = "mqtt"
    data_cagg_interval: str | None = None
    data_receive_schedule: str | None
    gsheet_id: str | None = None
    point: Point
    polygon: Polygon | None = None
    image_url: str | None = None
    spec: ProjectSpec

    # Project milestone dates
    commencement_of_construction_date: datetime.date | None = None
    financial_close_date: datetime.date | None = None
    notice_to_proceed_date: datetime.date | None = None
    mechanical_completion_date: datetime.date | None = None
    substantial_completion_date: datetime.date | None = None
    interconnection_approval_date: datetime.date | None = None
    performance_test_completion_date: datetime.date | None = None
    placed_in_service_date: datetime.date | None = None
    first_realtime_data_received_date: datetime.date | None = None
    first_data_backfilled_date: datetime.date | None = None

    # Interconnection details
    interconnecting_iso: str | None = None
    interconnecting_utility: str | None = None
    interconnecting_node_code: str | None = None
    interconnecting_substation: str | None = None
    interconnecting_voltage: float | None = None

    # Project status flags
    project_status_type_id: int | None = 2
    has_event_integration: bool = False
    has_expected_energy_integration: bool = False
    has_report_integration: bool = False
    has_quality_integration: bool = False
    has_block_layout: bool = False
    has_pv_pcs_layout: bool = False
    has_tracker_layout: bool = False
    has_pv_dc_combiner_layout: bool = False
    has_met_stations: bool = False
    has_pv_pcs_modules: bool = False
    has_pv_dc_combiners: bool = False
    has_trackers: bool = False
    has_bess_blocks: bool = False
    has_bess_pcss: bool = False
    has_bess_enclosures: bool = False
    has_bess_banks: bool = False
    has_bess_strings: bool = False
    has_backtracking: bool | None = None
    has_real_time_data: bool = False

    model_config = {"from_attributes": True}


class CompanyProject(BaseModel):
    """Companyproject model."""

    company_id: uuid.UUID
    project_id: uuid.UUID
    vector_store_id: str


class ProjectDataLastUpdated(BaseModel):
    """Projectdatalastupdated model."""

    project_id: uuid.UUID
    time_error: datetime.datetime | None
    time_empty: datetime.datetime | None
    time_last: datetime.datetime | None


class DeviceType(BaseModel):
    """Devicetype model."""

    device_type_id: int
    name_short: str
    name_long: str
    description: str | None

    model_config = {"from_attributes": True}


class DeviceModel(BaseModel):
    """Devicemodel model."""

    device_model_id: int
    device_type_id: int
    brand: str
    model: str

    model_config = {"from_attributes": True}


class Document(BaseModel):
    """Document model."""

    document_id: uuid.UUID
    name: str
    url: str
    contract_name: str | None = None


class Device(BaseModel):
    """Device model."""

    device_id: int
    device_id_path: str | None
    device_type_id: int
    device_model_id: int | None
    cec_pv_inverter_id: int | None
    cec_pv_module_id: int | None
    pv_module_id: int | None
    parent_device_id: int | None
    logical: bool
    name_short: str | None
    name_long: str | None
    capacity_dc: float | None
    capacity_ac: float | None
    point: Point | None
    polygon: MultiPolygon | None

    device_type: DeviceType | None = None
    name_full: str | None = None

    model_config = {"from_attributes": True}


class PVDCCombiner(BaseModel):
    """Pvdccombiner model."""

    device_id: int
    pv_module_id: int | None
    modules_per_pv_source_circuit: int
    modules_per_combiner: int


class SensorType(BaseModel):
    """Sensortype model."""

    sensor_type_id: int
    device_type_id: int
    name_short: str
    name_long: str
    name_metric: str
    unit: str | None
    description: str | None


class PGDataType(BaseModel):
    """Pgdatatype model."""

    pg_data_type_id: int
    name_short: str


class DataType(BaseModel):
    """Datatype model."""

    data_type_id: int
    name_short: str


class KPIType(BaseModel):
    """Kpitype model."""

    kpi_type_id: int
    device_type_id: int
    name_short: str
    name_long: str
    name_metric: str
    description: str | None
    unit: str | None
    aggregation_method: str
    device_type: DeviceType | None = None
    doc_url: str | None = None


class KPIInstance(BaseModel):
    """Kpiinstance model."""

    project_id: uuid.UUID
    kpi_type_id: int
    is_visible: bool
    kpi_type: KPIType | None = None


class DeviceDataObj(BaseModel):
    """Devicedataobj model."""

    device_values: dict[int, list[int | float | None]]


class DeviceAggregationObj(BaseModel):
    """Deviceaggregationobj model."""

    sum: list[float | None]
    mean: list[float | None]
    std: list[float | None]
    min: list[float | None]
    max: list[float | None]
    median: list[float | None]
    count: list[int | None]
    range: list[float | None]
    available_data: list[float | None]


class OperationalKPIDataObj(BaseModel):
    """Operationalkpidataobj model."""

    dates: list[datetime.date]
    project_data: list[float]
    weights: list[float | None] | None
    device_data_obj: DeviceDataObj | None
    device_aggregation_obj: DeviceAggregationObj | None


class OperationalKPIData(BaseModel):
    """Operationalkpidata model."""

    project_id: uuid.UUID
    kpi_type_id: int
    data: OperationalKPIDataObj


class TagV1(BaseModel):
    """Tag model."""

    tag_id: int
    in_tsdb: bool
    device_id: int
    sensor_type_id: int | None
    pg_data_type_id: int
    data_type_id: int | None
    name_short: str | None
    name_long: str | None
    name_scada: str
    scada_id: int | None
    scada_type: str | None
    unit_scada: str | None
    unit_offset: float | None
    unit_scale: float | None
    point: Point | None
    polygon: Polygon | None

    device: Device | None = None
    sensor_type: SensorType | None = None
    data_type: DataType | None = None
    status_lookup_id: int | None = None


class Tag(BaseModel):
    """
    Flat Tag model returned by v2 endpoint.
    Includes flattened fields from joined tables when deep=True.
    """

    tag_id: int
    in_tsdb: bool
    device_id: int
    sensor_type_id: int | None
    pg_data_type_id: int
    data_type_id: int | None
    name_short: str | None
    name_long: str | None
    name_scada: str
    scada_id: int | None
    scada_type: str | None
    unit_scada: str | None
    unit_offset: float | None
    unit_scale: float | None
    point: Point | None
    polygon: Polygon | None
    status_lookup_id: int | None = None

    # Flattened Device fields
    device_device_id: int | None = None
    device_device_id_path: str | None = None
    device_device_type_id: int | None = None
    device_device_model_id: int | None = None
    device_parent_device_id: int | None = None
    device_logical: bool | None = None
    device_name_short: str | None = None
    device_name_long: str | None = None
    device_capacity_dc: float | None = None
    device_capacity_ac: float | None = None
    device_point: Point | None = None
    device_polygon: MultiPolygon | None = None

    # Flattened DeviceType fields
    device_type_device_type_id: int | None = None
    device_type_name_short: str | None = None
    device_type_name_long: str | None = None
    device_type_description: str | None = None

    # Flattened SensorType fields
    sensor_type_sensor_type_id: int | None = None
    sensor_type_device_type_id: int | None = None
    sensor_type_name_short: str | None = None
    sensor_type_name_long: str | None = None
    sensor_type_name_metric: str | None = None
    sensor_type_unit: str | None = None
    sensor_type_description: str | None = None

    # Flattened DataType fields
    data_type_data_type_id: int | None = None
    data_type_name_short: str | None = None

    model_config = ConfigDict(from_attributes=True, extra="allow")


class Data(BaseModel):
    """Data model."""

    time: datetime.datetime
    tag_id: int
    value: Any


class DataTimeSeries(BaseModel):
    """Datatimeseries model."""

    x: list[str]
    y: list[float | str | None]
    y_range: list[float | str | None]
    yaxis: str
    name: str
    sensor_type_name: str
    device_name_long: str
    tag_name_scada: str
    tag_name_long: str
    device_id: int
    sensor_type_id: int
    tag_id: int


class _KPIProjectTemplateData(BaseModel):
    """kpiprojecttemplatedata model."""

    timestamps: list[datetime.datetime]
    values: list[float | None]


class KPIProjectTemplate(BaseModel):
    """Kpiprojecttemplate model."""

    data: _KPIProjectTemplateData


class _KPIDevicesTemplateData(BaseModel):
    """kpidevicestemplatedata model."""

    timestamps: list[datetime.datetime]
    names: list[str]
    values: list[list[float | None]]


class KPIDevicesTemplate(BaseModel):
    """Kpidevicestemplate model."""

    data: _KPIDevicesTemplateData


class Report(BaseModel):
    """Report model."""

    filename: str
    data_pdf: str


class ReportType(BaseModel):
    """Reporttype model."""

    model_config = ConfigDict(from_attributes=True)

    report_type_id: int
    name_short: str
    name_long: str
    doc_url: str | None = None
    description: str | None = None


class ReportInstance(BaseModel):
    """Reportinstance model."""

    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    report_type_id: int
    is_visible: bool
    report_type: ReportType | None = None


class ReportInstanceUpdate(BaseModel):
    """Reportinstanceupdate model."""

    report_type_id: int
    is_visible: bool


class ReportInstancesBulkUpdate(BaseModel):
    """Reportinstancesbulkupdate model."""

    report_instances: list[ReportInstanceUpdate]
    report_type_ids_to_delete: list[int] | None = None


class FailureMode(BaseModel):
    """Failuremode model."""

    failure_mode_id: int
    device_type_id: int
    name_short: str
    name_long: str


class FailureModeUpdate(BaseModel):
    """Failuremodeupdate model."""

    failure_mode_id: int


class RootCause(BaseModel):
    """Rootcause model."""

    root_cause_id: int
    device_type_id: int
    name_short: str
    name_long: str


class RootCauseUpdate(BaseModel):
    """Rootcauseupdate model."""

    root_cause_id: int


class Event(BaseModel):
    """Event model."""

    event_id: int
    device_id: int
    failure_mode_id: int
    root_cause_id: int | None
    time_start: datetime.datetime
    time_end: datetime.datetime | None
    time_detected: datetime.datetime
    time_last_analyzed: datetime.datetime | None
    loss_total_financial: float | None

    failure_mode: FailureMode | None = None
    root_cause: RootCause | None = None
    device: Device | None = None

    device_name_full: str | None = None
    version: str | None = None


class PaginatedEvent(BaseModel):
    """Paginatedevent model."""

    event_id: int
    device_name_full: str
    time_start: datetime.datetime
    time_end: datetime.datetime | None
    loss_daily_power: float | None
    loss_today_power: float | None
    loss_total_power: float | None
    loss_daily_financial: float | None
    loss_today_financial: float | None
    loss_total_financial: float | None
    root_cause: str


class EventSummary(BaseModel):
    """Eventsummary model."""

    event_id: int
    device_type_name: str
    device_name_full: str
    time_start: datetime.datetime
    time_end: datetime.datetime | None
    failure_mode: str
    root_cause: str
    loss_total_financial: float | None
    loss_total_energy: float | None
    loss_daily_financial: float | None
    loss_daily_energy: float | None


class EventCMMSTicket(BaseModel):
    """Eventcmmsticket model."""

    event_cmms_ticket_id: int
    event_id: int
    cmms_ticket_id: int
    created_by_user_id: str
    created_at: datetime.datetime


class GeoJSON(BaseModel):
    """Geojson model."""

    class Features(BaseModel):
        """Features model."""

        type: str
        properties: Any | None
        geometry: Point | Polygon | MultiPolygon

    type: str
    features: list[Features]


# --- Event Creation (bulk) ---
class BulkEventItem(BaseModel):
    """Bulkeventitem model."""

    device_id: int
    loss: float
    event_loss_type_id: int = 3
    anomaly_uuids: list[uuid.UUID] | None = None


class BulkCreateEventsRequest(BaseModel):
    """Bulkcreateeventsrequest model."""

    time_start: datetime.datetime
    time_end: datetime.datetime | None = None
    items: list[BulkEventItem]
    root_cause_id: int | None = None


class BulkCreateEventsResponse(BaseModel):
    """Bulkcreateeventsresponse model."""

    created_event_ids: list[int]


class SettlementPointMarket(BaseModel):
    """Settlementpointmarket model."""

    settlement_point_market_id: int
    name_short: str
    name_long: str


class SettlementPointType(BaseModel):
    """Settlementpointtype model."""

    settlement_point_type_id: int
    name_short: str
    name_long: str


class SettlementPointCore(BaseModel):
    """Settlementpointcore model."""

    settlement_point_id: int
    name: str
    settlement_point_type_id: int
    load_zone_id: int | None
    trading_hub_id: int | None


class SettlementPoint(SettlementPointCore):
    """Settlementpoint model."""

    settlement_point_type: SettlementPointType | None = None
    load_zone: SettlementPointCore | None = None
    trading_hub: SettlementPointCore | None = None


class QSE(BaseModel):
    """Qse model."""

    qse_id: int
    name_short: str
    name_long: str | None


class DME(BaseModel):
    """Dme model."""

    dme_id: int
    name_short: str
    name_long: str | None


class Resource(BaseModel):
    """Resource model."""

    resource_id: int
    name_gen: str
    name_load: str
    name_long: str
    county: str
    in_service: int
    capacity_power: float
    qse_id: int
    dme_id: int
    settlement_point_id: int

    qse: QSE | None = None
    dme: DME | None = None
    settlement_point: SettlementPoint | None = None


class Inspection(BaseModel):
    """Inspection model."""

    date: datetime.datetime | None
    inspection: str | None
    status: str | None
    trade: str | None
    id: int
    device_id: int


class Observation(BaseModel):
    """Observation model."""

    type: str | None
    national_type: str | None
    inspection_origin: str | None
    status: str | None
    created: datetime.datetime | None
    description: str | None
    spec_section: str | None
    trade_name: str | None
    priority: str | None
    impact_level: str | None
    id: int
    device_id: int


class CECPVInverter(BaseModel):
    """Cecpvinverter model."""

    manufacturer: str
    model_number: str
    hybrid_inverter: bool | None
    ul1741sb_certification: bool | None
    ul1741sa_testing: bool | None
    ul1741sa_13_volt_var: bool | None
    ul1741sa_freq_watt_volt_watt: bool | None
    ul1741sa_disable_permit_service: bool | None
    common_smart_inverter_profile: bool | None
    monitor_key_data_scheduling: bool | None
    description: str | None
    max_output_power_unity_pf: float | None
    nominal_voltage: float | None
    weighted_efficiency: float | None
    ul1741sb_certification_3rd_ed_entity: str | None
    ul1741sb_certification_3rd_ed_date: datetime.date | None
    ul1741sa_certification_sa8_sa13_entity: str | None
    ul1741sa_certification_sa8_sa13_date: datetime.date | None
    ul1741sa_certification_sa8_sa13_firmware_versions: str | None
    ul1741sa_13_volt_var_date: datetime.date | None
    ul1741sa_freq_watt_volt_watt_date: datetime.date | None
    ul1741sa_disable_permit_service_date: datetime.date | None
    inverter_csip_conformance_entity: str | None
    inverter_csip_conformance_date: datetime.date | None
    monitor_key_data_scheduling_att: str | None
    notes: str | None
    built_in_meter: bool | None
    microinverter: bool | None
    night_tare_loss: float | None
    power_rating_40_deg_c: float | None
    night_tare_loss_40_deg_c: float | None
    voltage_minimum: float | None
    voltage_nominal: float | None
    voltage_maximum: float | None
    power_level_10: float | None
    power_level_20: float | None
    power_level_30: float | None
    power_level_50: float | None
    power_level_75: float | None
    power_level_100: float | None
    efficiency_vmin_10: float | None
    efficiency_vmin_20: float | None
    efficiency_vmin_30: float | None
    efficiency_vmin_50: float | None
    efficiency_vmin_75: float | None
    efficiency_vmin_100: float | None
    efficiency_vmin_wtd: float | None
    efficiency_vnom_10: float | None
    efficiency_vnom_20: float | None
    efficiency_vnom_30: float | None
    efficiency_vnom_50: float | None
    efficiency_vnom_75: float | None
    efficiency_vnom_100: float | None
    efficiency_vnom_wtd: float | None
    efficiency_vmax_10: float | None
    efficiency_vmax_20: float | None
    efficiency_vmax_30: float | None
    efficiency_vmax_50: float | None
    efficiency_vmax_75: float | None
    efficiency_vmax_100: float | None
    efficiency_vmax_wtd: float | None
    grid_support_listing_date: datetime.date | None
    last_update: datetime.date | None


class CECPVInverterCreate(CECPVInverter):
    """Cecpvinvertercreate model."""


class CECPVInverterBulkCreate(BaseModel):
    """Cecpvinverterbulkcreate model."""

    inverters: list[CECPVInverterCreate]


class CECPVInverterWithID(CECPVInverter):
    """Cecpvinverterwithid model."""

    cec_pv_inverter_id: int


class PVModule(BaseModel):
    """Pvmodule model."""

    pv_module_id: int | None = Field(
        ...,
        description="Unique identifier for the PV module",
    )
    company_id: uuid.UUID
    device_model_id: int | None = Field(
        default=None,
        description="Foreign key to device_models table",
    )
    manufacturer: str = Field(..., description="Name of the PV module manufacturer")
    model: str = Field(..., description="Model name of the PV module")
    technology: str = Field(..., description="CdTe / c_Si")
    bifaciality_factor: float = Field(
        ..., description="Ratio of backside to frontside efficiency [0.0, 1.0]"
    )
    pmax: float = Field(..., description="Maximum power (Pmax) in Watts")
    isc: float = Field(..., description="Short-circuit current (Isc) in Amps")
    voc: float = Field(..., description="Open-circuit voltage (Voc) in Volts")
    imp: float = Field(..., description="Current at maximum power point (Imp) in Amps")
    vmp: float = Field(..., description="Voltage at maximum power point (Vmp) in Volts")
    gamma_pmax: float = Field(..., description="Temperature coefficient of Pmax (%/°C)")
    alpha_isc_relative: float | None = Field(
        default=None,
        description="Relative temperature coefficient of Isc (%/°C)",
    )
    beta_voc_relative: float | None = Field(
        default=None,
        description="Relative temperature coefficient of Voc (%/°C)",
    )
    alpha_isc: float | None = Field(
        default=None,
        description="Absolute temperature coefficient of Isc (A/°C)",
    )
    beta_voc: float | None = Field(
        default=None,
        description="Absolute temperature coefficient of Voc (V/°C)",
    )
    warranted_degradation_rate: float = Field(
        ...,
        description="Annual warranted degradation rate (%)",
    )
    warranted_degradation_initial: float = Field(
        ...,
        description="Initial warranted degradation (%)",
    )
    length: float = Field(..., description="Length of the PV module in ( mm )")
    width: float = Field(..., description="Width of the PV module in ( mm )")
    frame_overhang: float = Field(
        ...,
        description="Frame overhang of the PV module in ( mm )",
    )
    has_ar_coating: bool = Field(
        ...,
        description="Indicates if the module has anti-reflective coating",
    )
    cells_in_series: int = Field(..., description="Number of cells connected in series")
    cells_in_parallel: int = Field(
        ..., description="Number of cells connected in parallel"
    )
    photocurrent: float = Field(..., description="Light generated current in ( A )")
    diode_saturation_current: float = Field(
        ...,
        description="Diode saturation current in ( A )",
    )
    r_series: float = Field(..., description="Series resistance in ( Ω )")
    r_shunt: float = Field(..., description="Shunt resistance in ( Ω )")
    modified_ideality_factor: float = Field(..., description="Modified ideality factor")
    eg: float = Field(..., description="Bandgap energy in ( eV )")
    degdt: float = Field(..., description="delta eg over delta temperature")
    data_source: str = Field(..., description="Source of the PV module data")
    family: str = Field(..., description="Indicates if the module is part of a family")
    half_cut: bool = Field(
        ...,
        description="Indicates if the module uses half-cut cells",
    )


class CECPVModule(BaseModel):
    # --- Allow configure from dictionary ---
    """Cecpvmodule model."""

    model_config = ConfigDict(from_attributes=True)

    # --- Parameters ---
    cec_pv_module_id: int
    manufacturer: str
    model_number: str
    description: str | None
    safety_certification: str | None
    nameplate_pmax: float | None
    ptc: float | None
    notes: str | None
    design_qualification: datetime.date | None
    performance_evaluation: str | None
    family: str | None
    technology: str | None
    a_c: float | None
    n_s: int | None
    n_p: int | None
    bipv: bool | None
    nameplate_isc: float | None
    nameplate_voc: float | None
    nameplate_ipmax: float | None
    nameplate_vpmax: float | None
    average_noct: float | None
    gamma_pmax: float | None
    alpha_isc: float | None
    beta_voc: float | None
    alpha_ipmax: float | None
    beta_vpmax: float | None
    ipmax_low: float | None
    vpmax_low: float | None
    ipmax_noct: float | None
    vpmax_noct: float | None
    mounting: str | None
    type: str | None
    short_side: float | None
    long_side: float | None
    geometric_multiplier: float | None
    p2p_ref: float | None
    cec_listing_date: datetime.date | None
    last_update: datetime.date | None


class CECPVModuleCreate(CECPVModule):
    """Cecpvmodulecreate model."""


class CECPVModuleBulkCreate(BaseModel):
    """Cecpvmodulebulkcreate model."""

    modules: list[CECPVModuleCreate]


class CECPVModuleWithID(CECPVModule):
    """Cecpvmodulewithid model."""

    cec_pv_module_id: int


class Inverter(BaseModel):
    """Inverter model."""

    inverter_id: int | None
    manufacturer: str
    model: str
    company_id: uuid.UUID
    device_model_id: int | None = None

    # Operating window parameters
    voltage_mpp_min: float
    voltage_mpp_max: float
    voltage_start_up: float
    voltage_min: float
    voltage_max: float
    current_max: float

    # Temperature-dependent power characteristics
    power_max_at_reference_temp: list[float]
    reference_temp: list[float]

    # Inverter efficiency reference parameters
    voltage_nominal_efficiency: list[float]
    efficiency_at_low_voltage: list[list[float]]
    efficiency_at_mid_voltage: list[list[float]]
    efficiency_at_high_voltage: list[list[float]]

    # Inverter efficiency parameters
    power_start_up: float
    power_ac_nominal: float
    power_dc_nominal: float
    voltage_dc_nominal: float
    c0: float
    c1: float
    c2: float
    c3: float
    night_tare: float


class Transformer(BaseModel):
    """Transformer model."""

    transformer_id: int
    manufacturer: str
    model: str
    no_load_loss: float
    load_loss: float
    rating: float


class ContractCreate(BaseModel):
    """Contractcreate model."""

    project_id: uuid.UUID
    document_id: uuid.UUID
    company_id_provider: uuid.UUID
    company_id_counter: uuid.UUID
    execution_date: datetime.date
    # Optional extended fields
    contract_category_id: int | None = None
    contract_category_name_short: str | None = None
    term_start_date: datetime.date | None = None
    term_end_date: datetime.date | None = None
    counter_contact_addressee: str | None = None
    counter_contact_email: str | None = None
    counter_contact_address: str | None = None
    contract_summary: str | None = None


class Contract(BaseModel):
    """Contract model."""

    project_id: uuid.UUID
    document_id: uuid.UUID
    company_id_provider: uuid.UUID | None = None
    company_id_counter: uuid.UUID | None = None
    execution_date: datetime.date | None = None


# --- PV Budgeted Performance ---
class PVBudgetedSeriesIn(BaseModel):
    """Pvbudgetedseriesin model."""

    p_value: str
    frequency: str
    soiling_mode: str | None = None
    soiling_fixed_percentage: float | None = None
    tmy_source: str | None = None
    model_version: str | None = None
    filename: str | None = None


class PVBudgetedSeries(PVBudgetedSeriesIn):
    """Pvbudgetedseries model."""

    pv_budgeted_series_id: int


class PVBudgetedDataRow(BaseModel):
    """Pvbudgeteddatarow model."""

    time_stamp: datetime.datetime
    poi_ac_power: float
    ghi: float | None = None
    poa: float
    temperature: float | None = None
    soiling_percentage: float | None = None


class PVBudgetedBulkUpsertRequest(BaseModel):
    """Pvbudgetedbulkupsertrequest model."""

    pv_budgeted_series_id: int | None = None
    series: PVBudgetedSeriesIn | None = None
    rows: list[PVBudgetedDataRow]


class ContractWithCompany(BaseModel):
    """Contractwithcompany model."""

    contract_id: int
    project_id: uuid.UUID
    document_id: uuid.UUID
    company_id_provider: uuid.UUID
    company_id_counter: uuid.UUID
    execution_date: datetime.datetime  # TODO
    name_short: str
    name_long: str
    document_url: str | None
    s3_key: str | None
    openai_file_id: str | None = None
    # Optional extended fields
    contract_category_id: int | None = None
    category_name_short: str | None = None
    category_name_long: str | None = None
    term_start_date: datetime.date | None = None
    term_end_date: datetime.date | None = None
    counter_contact_addressee: str | None = None
    counter_contact_email: str | None = None
    counter_contact_address: str | None = None
    contract_summary: str | None = None


class ContractCategory(BaseModel):
    """Contractcategory model."""

    contract_category_id: int
    name_short: str
    name_long: str


class CompanyCreate(BaseModel):
    """Companycreate model."""

    name_short: str
    name_long: str


class Company(CompanyCreate):
    """Company model."""

    company_id: uuid.UUID


# --- Admin Teams ---
class TeamCreate(BaseModel):
    """Teamcreate model."""

    name_long: str


class Team(TeamCreate):
    """Team model."""

    team_id: uuid.UUID
    company_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime


class UserBasic(BaseModel):
    """Userbasic model."""

    user_id: str
    name_long: str


class TeamWithMembers(Team):
    """Teamwithmembers model."""

    members: list[UserBasic]


class TeamMemberAdd(BaseModel):
    """Teammemberadd model."""

    user_id: str


class TeamUpdate(BaseModel):
    """Teamupdate model."""

    name_long: str


class ContractKPIs(BaseModel):
    """Contractkpis model."""

    contract_id: int
    kpi_type_id: int
    threshold: dict | None
    liquidated_damages: dict | None
    claim_howto: dict | None
    provider_responsible: bool | None
    provider_company: str | None = None
    counter_company: str | None = None
    document_url: str | None = None


class KPISummary(BaseModel):
    """Kpisummary model."""

    kpi_type_id: int
    title: str
    value: float | None = None
    info: str | None = None
    unit: str | None = None
    prefix: str | None = None
    change: float | None = None
    valColor: str | None = None
    link: str
    is_visible: bool | None = None
    contract_id: int | None = None
    threshold: dict | None = None
    ytd_value: float | None = None
    aggregation_method: str | None = None

    model_config = {"from_attributes": True}


class KPITypeWithContracts(KPIType):
    """Kpitypewithcontracts model."""

    contracts: list[ContractWithCompany] = []
    contract_kpis: list[ContractKPIs] = []


class ContractInfo(BaseModel):
    """Contractinfo model."""

    contract_id: int
    project_id: uuid.UUID
    execution_date: datetime.date
    provider_company: str
    counter_company: str

    model_config = {"from_attributes": True}


class KPITypeWithContractInfo(KPIType):
    """Kpitypewithcontractinfo model."""

    contract_kpis: list[ContractKPIs] = []
    contracts: list[ContractInfo] = []
    device_type_name: str | None = None
    is_visible: bool | None = False

    model_config = {"from_attributes": True}


class CMMSProvider(BaseModel):
    """Cmmsprovider model."""

    cmms_provider_id: int
    name_short: str
    name_long: str


class CMMSIntegration(BaseModel):
    """Cmmsintegration model."""

    cmms_integration_id: int
    project_id: uuid.UUID
    cmms_provider_id: int
    project_name: str | None
    domain_name: str | None


class CMMSPermission(BaseModel):
    """Cmmspermission model."""

    cmms_integration_id: int
    company_id: uuid.UUID
    can_view: bool


class PVRackings(BaseModel):
    """Pvrackings model."""

    racking_id: int | None = Field(description="Primary Key")
    company_id: uuid.UUID
    device_model_id: int | None = Field(
        default=None,
        description="Foreign key to device_models table",
    )
    racking_type_id: int = Field(description="Foreign Key to racking_types")
    manufacturer: str = Field(description="Manufacturer of the racking")
    model: str = Field(description="Model of the racking")
    max_rotation_angle: float = Field(description="Maximum rotation angle in degrees")
    min_rotation_angle: float = Field(description="Minimum rotation angle in degrees")
    wind_stow_angle: float = Field(description="Wind stow angle in degrees")
    wind_stow_threshold: float = Field(
        description="Wind stow threshold in meters per second",
    )
    hail_stow_angle: float = Field(description="Hail stow angle in degrees")
    snow_stow_angle: float = Field(description="Snow stow angle in degrees")


class CalendarItemCategoryBase(BaseModel):
    """Calendaritemcategorybase model."""

    short_name: str
    long_name: str
    color_code: str


class CalendarItemCategoryCreate(CalendarItemCategoryBase):
    """Calendaritemcategorycreate model."""


class CalendarItemCategoryUpdate(BaseModel):
    """Calendaritemcategoryupdate model."""

    short_name: str | None = None
    long_name: str | None = None
    color_code: str | None = None


class CalendarItemCategoryInDBBase(CalendarItemCategoryBase):
    """Calendaritemcategoryindbbase model."""

    category_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {
        "from_attributes": True,
    }


class CalendarItemCategory(CalendarItemCategoryInDBBase):
    """Calendaritemcategory model."""


class CalendarItemBase(BaseModel):
    """Calendaritembase model."""

    title: str
    description: str | None = None
    calendar_item_category_id: uuid.UUID
    start_time: datetime.datetime
    end_time: datetime.datetime
    all_day: bool
    rrule: str | None = None
    timezone: str = "UTC"  # Default to UTC if not specified
    notify_offsets: list[str] | None = None
    notify_method: list[str] | None = None


class CalendarItemCreate(CalendarItemBase):
    # Optional assignees at creation time
    """Calendaritemcreate model."""

    assignee_user_ids: list[str] | None = None
    assignee_team_ids: list[uuid.UUID] | None = None


class CalendarItemInDBBase(CalendarItemBase):
    """Calendaritemindbbase model."""

    calendar_item_id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    color: str | None = None  # Add color field to be included in response
    exdates: list[datetime.date] | None = None  # Add exdates for cancelled occurrences
    # Assignments (ids only; names resolved on frontend)
    assignee_user_ids: list[str] | None = None
    assignee_team_ids: list[uuid.UUID] | None = None

    model_config = {
        "from_attributes": True,
    }


class CalendarItem(CalendarItemInDBBase):
    """Calendaritem model."""


# Models for CalendarItemException
class CalendarItemExceptionBase(BaseModel):
    """Calendaritemexceptionbase model."""

    exception_date: datetime.date
    is_cancelled: bool = False
    override_start_time: datetime.datetime | None = None
    override_end_time: datetime.datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CalendarItemExceptionCreate(CalendarItemExceptionBase):
    """Calendaritemexceptioncreate model."""

    calendar_item_id: uuid.UUID  # Needed when creating/linking the exception
    # exception_date must be provided on create


class CalendarItemExceptionUpdate(BaseModel):
    # For updates, at least one of these should be provided.
    # exception_date is part of the unique key and typically
    # wouldn't be changed via an update;
    """Calendaritemexceptionupdate model."""

    is_cancelled: bool | None = None
    override_start_time: datetime.datetime | None = None
    # To clear a datetime, pass None. If not provided, it's unchanged.
    override_end_time: datetime.datetime | None = None


class CalendarItemException(CalendarItemExceptionBase):
    """Calendaritemexception model."""

    exception_id: uuid.UUID
    calendar_item_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime


class DroneIntegrationBase(BaseModel):
    """Droneintegrationbase model."""

    drone_integration_id: int
    project_id: uuid.UUID
    drone_provider_id: int
    provider_project_id: str


class DroneIntegration(DroneIntegrationBase):
    """Droneintegration model."""

    model_config = ConfigDict(from_attributes=True)


class DroneProviderBase(BaseModel):
    """Droneproviderbase model."""

    drone_provider_id: int
    name_short: str
    name_long: str


class DroneProvider(DroneProviderBase):
    """Droneprovider model."""

    model_config = ConfigDict(from_attributes=True)


class DroneProviderCreate(DroneProviderBase):
    """Droneprovidercreate model."""


class DronePermissionBase(BaseModel):
    """Dronepermissionbase model."""

    drone_integration_id: int
    company_id: uuid.UUID
    can_view: bool


class DronePermission(DronePermissionBase):
    """Dronepermission model."""

    model_config = ConfigDict(from_attributes=True)


class DronePermissionCreate(DronePermissionBase):
    """Dronepermissioncreate model."""


class DronePermissionUpdate(BaseModel):
    """Dronepermissionupdate model."""

    can_view: bool


class DroneIntegrationCreate(BaseModel):
    """Droneintegrationcreate model."""

    project_id: uuid.UUID
    drone_provider_id: int
    provider_project_id: str


class DroneProviderUpdate(BaseModel):
    """Droneproviderupdate model."""

    name_short: str
    name_long: str


class DroneIntegrationUpdate(BaseModel):
    """Droneintegrationupdate model."""

    project_id: uuid.UUID
    drone_provider_id: int
    provider_project_id: str


class SiteInfo(BaseModel):
    """Siteinfo model."""

    site_uuid: uuid.UUID
    site_id: int
    site_name: str
    site_capacity_mw: float


class Grade(BaseModel):
    """Grade model."""

    site_impact_category: str
    grade: str
    power_loss_kw: float
    power_loss_percent: float
    affected_modules: int
    affected_modules_percent: float


class ZeitviewObservation(BaseModel):
    """Zeitviewobservation model."""

    description: str


class ZeitviewInspection(BaseModel):
    """Zeitviewinspection model."""

    inspection_uuid: uuid.UUID
    inspection_date: str
    upload_date: str
    site: SiteInfo
    service_tier: str | None = None
    total_power_loss_kw: float | None = None
    total_power_loss_percent: float | None = None
    total_affected_modules: int | None = None
    grades: list[Grade]
    observations: list[ZeitviewObservation]
    report_summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DroneInspectionCreate(BaseModel):
    """Droneinspectioncreate model."""

    inspection_uuid: uuid.UUID
    inspection_time: datetime.datetime
    upload_time: datetime.datetime
    service_tier: str | None = None
    total_power_loss_kw: float | None = None
    total_power_loss_percent: float | None = None
    total_affected_modules: int | None = None
    report_summary: str | None = None


class DroneInspection(BaseModel):
    """Droneinspection model."""

    inspection_uuid: uuid.UUID
    inspection_time: datetime.datetime
    upload_time: datetime.datetime
    service_tier: str | None = None
    total_power_loss_kw: float | None = None
    total_power_loss_percent: float | None = None
    total_affected_modules: int | None = None
    report_summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DroneAnomalyBase(BaseModel):
    """Droneanomalybase model."""

    anomaly_uuid: uuid.UUID
    inspection_uuid: uuid.UUID
    event_id: int | None = None
    stack_id: str | None = None
    ir_signal: str | None = None
    rgb_signal: str | None = None
    ir_image_url: str | None = None
    rgb_image_url: str | None = None
    subsystem: str | None = None
    remediation_category: str | None = None
    energy_loss_weighting: float | None = None
    power_loss_kw: float | None = None
    location_lat: float | None = None
    location_lon: float | None = None
    client_status_id: int | None = None


class DroneAnomaly(DroneAnomalyBase):
    """Droneanomaly model."""

    model_config = ConfigDict(from_attributes=True)


class DroneAnomalyCreate(DroneAnomalyBase):
    """Droneanomalycreate model."""


class ContractSearchResult(BaseModel):
    """Contractsearchresult model."""

    text: str
    filename: str
    score: float


class ContractSearchResponse(BaseModel):
    """Contractsearchresponse model."""

    search_results: list[ContractSearchResult]


class Message(BaseModel):
    """Message model."""

    message: str


class CMMSTicket(BaseModel):
    """CMMSTicket model."""

    cmms_ticket_id: int
    cmms_integration_id: int
    db_created_at: datetime.datetime
    db_updated_at: datetime.datetime
    key: str
    source_id: int
    source_created_at: datetime.datetime | None = None
    due_date: datetime.datetime | None = None
    summary: str | None = None
    summary_long: str | None = None
    status: str | None = None
    status_change_at: datetime.datetime | None = None
    priority: str | None = None
    reporter: str | None = None
    assigned_to: str | None = None
    location: str | None = None
    cmms_device_id: str | None = None
    cmms_device_name: str | None = None
    link: str | None = None
    json_raw: dict | None = None
