"""Starlette Admin configuration for core SQLAlchemy models."""

from __future__ import annotations

import copy
import uuid
from typing import Any, ClassVar

from core.models import (
    Company,
    Device,
    DeviceModel,
    DeviceType,
    Event,
    KPIInstance,
    KPIType,
    Project,
    ProjectType,
    SensorType,
    Tag,
    User,
)
from sqlalchemy import String, cast, or_
from starlette.datastructures import FormData
from starlette.requests import Request
from starlette_admin import DropDown
from starlette_admin._types import RequestAction
from starlette_admin.contrib.sqla import Admin, ModelView
from starlette_admin.fields import BaseField, IntegerField, StringField


class UUIDField(StringField):
    """Parse UUID form values eagerly instead of relying on DB coercion."""

    async def parse_form_data(
        self,
        request: Request,
        form_data: FormData,
        action: RequestAction,
    ) -> uuid.UUID | None:
        value = await super().parse_form_data(request, form_data, action)
        if value in (None, ""):
            return None
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError):
            return None


class SQLAdminParityView(ModelView):
    """Restore the old SQLAdmin view permissions and search behavior."""

    allow_create: ClassVar[bool] = True
    allow_edit: ClassVar[bool] = True
    allow_delete: ClassVar[bool] = True
    list_fields: ClassVar[tuple[str, ...]] = ()
    list_query_joins: ClassVar[tuple[Any, ...]] = ()
    search_columns: ClassVar[tuple[Any, ...]] = ()

    def __init__(self, model: type[Any]):
        self.fields = [
            copy.deepcopy(field) if isinstance(field, BaseField) else field
            for field in self.fields
        ]
        if self.list_fields:
            field_names = [
                field.name if isinstance(field, BaseField) else field
                for field in self.fields
            ]
            self.exclude_fields_from_list = [
                field_name
                for field_name in field_names
                if field_name not in self.list_fields
            ]
        super().__init__(model)

    def can_create(self, request: Request) -> bool:
        return self.allow_create

    def can_edit(self, request: Request) -> bool:
        return self.allow_edit

    def can_delete(self, request: Request) -> bool:
        return self.allow_delete

    def get_list_query(self):
        stmt = super().get_list_query()
        for join_attr in self.list_query_joins:
            stmt = stmt.outerjoin(join_attr)
        return stmt

    def get_count_query(self):
        stmt = super().get_count_query()
        for join_attr in self.list_query_joins:
            stmt = stmt.outerjoin(join_attr)
        return stmt

    def get_search_query(self, request: Request, term: str):
        if not self.search_columns:
            return super().get_search_query(request, term)
        clauses = [
            cast(column, String).ilike(f"%{term}%") for column in self.search_columns
        ]
        return or_(*clauses)


class CompanyView(SQLAdminParityView):
    label = "Companies"
    allow_create = False
    allow_edit = False
    allow_delete = False
    fields = [
        "company_id",
        "name_short",
        "name_long",
    ]
    list_fields = (
        "company_id",
        "name_short",
        "name_long",
    )
    searchable_fields = ["name_short", "name_long"]
    sortable_fields = ["company_id", "name_short"]
    fields_default_sort = ["name_short"]
    search_columns = (Company.name_short, Company.name_long)


class UserView(SQLAdminParityView):
    label = "Users"
    fields = [
        "user_id",
        "name_long",
        IntegerField("user_type_id"),
        UUIDField("company_id"),
        "api_key",
    ]
    list_fields = (
        "user_id",
        "name_long",
        "user_type_id",
        "company_id",
    )
    exclude_fields_from_create = ["user_id"]
    exclude_fields_from_edit = ["user_id"]
    searchable_fields = ["user_id", "name_long"]
    sortable_fields = ["user_id", "name_long"]
    fields_default_sort = ["name_long"]
    search_columns = (User.user_id, User.name_long)


class ProjectView(SQLAdminParityView):
    label = "Projects"
    allow_create = False
    allow_edit = False
    allow_delete = False
    fields = [
        UUIDField("project_id"),
        "project_id_int",
        IntegerField("project_type_id"),
        IntegerField("project_status_type_id"),
        "name_short",
        "name_long",
        "data_table",
        "data_interval",
        "data_cagg_interval",
        "data_receive_schedule",
        "commencement_of_construction_date",
        "financial_close_date",
        "notice_to_proceed_date",
        "mechanical_completion_date",
        "substantial_completion_date",
        "interconnection_approval_date",
        "performance_test_completion_date",
        "cod",
        "placed_in_service_date",
        "first_realtime_data_received_date",
        "first_data_backfilled_date",
        "address",
        "image_url",
        "elevation",
        "time_zone",
        "interconnecting_iso",
        "interconnecting_utility",
        "interconnecting_node_code",
        "interconnecting_substation",
        "interconnecting_voltage",
        "poi",
        "capacity_dc",
        "capacity_ac",
        "capacity_bess_power_ac",
        "capacity_bess_energy_bol_dc",
        "has_event_integration",
        "has_expected_energy_integration",
        "has_report_integration",
        "has_quality_integration",
        "has_block_layout",
        "has_pv_pcs_layout",
        "has_tracker_layout",
        "has_pv_dc_combiner_layout",
        "has_met_stations",
        "has_pv_pcs_modules",
        "has_pv_dc_combiners",
        "has_trackers",
        "has_bess_blocks",
        "has_bess_pcss",
        "has_bess_enclosures",
        "has_bess_banks",
        "has_bess_strings",
        "has_backtracking",
        "has_real_time_data",
        "ppa",
        "spec",
        "gsheet_id",
        "last_updated",
        StringField("last_updated_by"),
        UUIDField("owner"),
        "database_provider",
    ]
    list_fields = (
        "project_id",
        "name_short",
        "name_long",
        "project_type_id",
        "project_status_type_id",
        "cod",
    )
    searchable_fields = ["name_short", "name_long"]
    sortable_fields = ["project_id", "name_short", "cod"]
    fields_default_sort = ["name_short"]
    search_columns = (Project.name_short, Project.name_long)


class ProjectTypeView(SQLAdminParityView):
    label = "Project Types"
    allow_create = False
    allow_edit = False
    allow_delete = False
    fields = [
        "project_type_id",
        "name_short",
        "name_long",
    ]
    list_fields = (
        "project_type_id",
        "name_short",
        "name_long",
    )
    searchable_fields = ["name_short", "name_long"]
    sortable_fields = ["project_type_id", "name_short"]
    fields_default_sort = ["name_short"]
    search_columns = (ProjectType.name_short, ProjectType.name_long)


class DeviceView(SQLAdminParityView):
    label = "Devices"
    allow_create = False
    allow_delete = False
    fields = [
        "device_id",
        "name_short",
        "name_long",
        StringField(
            "device_type",
            label="Device type",
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        "logical",
        IntegerField("device_type_id"),
        IntegerField("device_model_id"),
        IntegerField("cec_pv_inverter_id"),
        IntegerField("cec_pv_module_id"),
        IntegerField("pv_module_id"),
        IntegerField("parent_device_id"),
        "capacity_dc",
        "capacity_ac",
        "capacity_energy_dc",
    ]
    list_fields = (
        "device_id",
        "name_short",
        "name_long",
        "device_type",
        "logical",
    )
    exclude_fields_from_edit = ["device_id"]
    searchable_fields = ["name_short", "name_long", "device_type"]
    sortable_fields = ["device_id", "name_short", "device_type"]
    sortable_field_mapping = {"device_type": Device.device_type_id}
    fields_default_sort = ["device_id"]
    list_query_joins = (Device.device_type,)
    search_columns = (Device.name_short, Device.name_long, DeviceType.name_long)


class SensorTypeView(SQLAdminParityView):
    label = "Sensor Types"
    allow_create = False
    allow_edit = False
    allow_delete = False
    fields = [
        "sensor_type_id",
        IntegerField("device_type_id"),
        "name_short",
        "name_long",
        "name_metric",
        "unit",
        "description",
    ]
    list_fields = (
        "sensor_type_id",
        "name_short",
        "name_long",
    )
    searchable_fields = ["name_short", "name_long"]
    sortable_fields = ["sensor_type_id", "name_short"]
    fields_default_sort = ["name_short"]
    search_columns = (SensorType.name_short, SensorType.name_long)


class DeviceModelView(SQLAdminParityView):
    name = "Device Model"
    label = "Device Models"
    allow_delete = False
    fields = [
        "device_model_id",
        IntegerField("device_type_id"),
        "brand",
        "model",
    ]
    exclude_fields_from_create = ["device_model_id"]
    exclude_fields_from_edit = ["device_model_id"]
    searchable_fields = ["brand", "model"]
    sortable_fields = ["device_model_id", "device_type_id", "brand", "model"]
    fields_default_sort = ["device_model_id"]
    search_columns = (DeviceModel.brand, DeviceModel.model)


class TagView(SQLAdminParityView):
    label = "Tags"
    allow_create = False
    allow_edit = False
    allow_delete = False
    fields = [
        "tag_id",
        "name_short",
        "name_long",
        "name_scada",
        IntegerField("device_id"),
        StringField(
            "sensor_type",
            label="Sensor type",
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        "in_tsdb",
        IntegerField("sensor_type_id"),
        IntegerField("pg_data_type_id"),
        IntegerField("data_type_id"),
        "scada_id",
        "scada_type",
        "unit_scada",
        "unit_offset",
        "unit_scale",
        IntegerField("status_lookup_id"),
    ]
    list_fields = (
        "tag_id",
        "name_short",
        "name_long",
        "name_scada",
        "device_id",
        "sensor_type",
        "in_tsdb",
    )
    searchable_fields = ["name_short", "name_long", "name_scada"]
    sortable_fields = ["tag_id", "name_short", "device_id", "sensor_type"]
    sortable_field_mapping = {"sensor_type": Tag.sensor_type_id}
    fields_default_sort = ["tag_id"]
    search_columns = (Tag.name_short, Tag.name_long, Tag.name_scada)


class KPITypeView(SQLAdminParityView):
    name = "KPI Type"
    label = "KPI Types"
    fields = [
        "kpi_type_id",
        IntegerField("device_type_id"),
        IntegerField("project_type_id"),
        "name_short",
        "name_long",
        "name_metric",
        "description",
        "unit",
        "aggregation_method",
        "doc_url",
        "critical_low",
        "warning_low",
        "warning_high",
        "critical_high",
    ]
    list_fields = (
        "kpi_type_id",
        "name_long",
        "device_type_id",
        "unit",
        "aggregation_method",
        "critical_low",
        "warning_low",
        "warning_high",
        "critical_high",
    )
    searchable_fields = ["name_short", "name_long", "name_metric"]
    sortable_fields = [
        "kpi_type_id",
        "name_short",
        "name_long",
        "device_type_id",
    ]
    fields_default_sort = ["name_short"]
    search_columns = (KPIType.name_short, KPIType.name_long, KPIType.name_metric)


class KPIInstanceView(SQLAdminParityView):
    name = "KPI Instance"
    label = "KPI Instances"
    form_include_pk = True
    fields = [
        StringField(
            "project",
            label="Project",
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        StringField(
            "kpi_type",
            label="KPI type",
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        "is_visible",
        UUIDField("project_id"),
        IntegerField("kpi_type_id"),
    ]
    list_fields = (
        "project",
        "kpi_type",
        "is_visible",
    )
    exclude_fields_from_edit = ["project_id", "kpi_type_id"]
    searchable_fields = ["project", "kpi_type"]
    sortable_fields = ["project", "kpi_type"]
    sortable_field_mapping = {
        "project": KPIInstance.project_id,
        "kpi_type": KPIInstance.kpi_type_id,
    }
    fields_default_sort = ["project"]
    search_columns = (KPIInstance.project_id, KPIInstance.kpi_type_id)


class EventView(SQLAdminParityView):
    label = "Events"
    allow_create = False
    allow_edit = False
    allow_delete = False
    fields = [
        "event_id",
        IntegerField("device_id"),
        IntegerField("failure_mode_id"),
        IntegerField("root_cause_id"),
        "time_start",
        "time_end",
        "time_detected",
        "time_last_analyzed",
        "loss_total_financial",
        "loss_daily_financial",
        "version",
    ]
    list_fields = (
        "event_id",
        "device_id",
        "failure_mode_id",
        "root_cause_id",
        "time_start",
        "time_end",
        "time_detected",
        "loss_total_financial",
    )
    searchable_fields = []
    sortable_fields = ["event_id", "device_id", "time_start", "time_end"]
    fields_default_sort = [("time_start", True)]


def setup_admin_views(*, admin: Admin) -> None:
    """Register Starlette Admin views with the old SQLAdmin surface area."""
    admin.add_view(
        DropDown(
            "Admin Schema",
            views=[
                CompanyView(Company),
                UserView(User),
            ],
        )
    )
    admin.add_view(
        DropDown(
            "Operational Schema",
            views=[
                ProjectView(Project),
                ProjectTypeView(ProjectType),
                DeviceModelView(DeviceModel),
                SensorTypeView(SensorType),
                KPITypeView(KPIType),
                KPIInstanceView(KPIInstance),
            ],
        )
    )
    admin.add_view(
        DropDown(
            "Project Schema",
            views=[
                DeviceView(Device),
                TagView(Tag),
                EventView(Event),
            ],
        )
    )
