"""SQLAdmin configuration and views for core models."""

from core.models import (
    Company,
    Device,
    DeviceModel,
    Event,
    KPIInstance,
    Project,
    ProjectType,
    SensorType,
    Tag,
    User,
)
from sqladmin import Admin, ModelView


class CompanyAdmin(ModelView, model=Company):
    """Admin view for Company model."""

    name_plural = "Companies"
    category = "Admin Schema"

    # READ-ONLY MODE - No modifications allowed
    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        Company.company_id,
        Company.name_short,
        Company.name_long,
    ]
    column_searchable_list = [Company.name_short, Company.name_long]
    column_sortable_list = [Company.company_id, Company.name_short]
    column_default_sort = [(Company.name_short, False)]

    form_excluded_columns = [Company.company_id]  # Auto-generated UUID


class UserAdmin(ModelView, model=User):
    """Admin view for User model."""

    category = "Admin Schema"

    can_create = True
    can_edit = True
    can_delete = True

    column_list = [
        User.user_id,
        User.name_long,
        User.user_type_id,
        User.company_id,
    ]
    column_searchable_list = [User.user_id, User.name_long]
    column_sortable_list = [User.user_id, User.name_long]
    column_default_sort = [(User.name_long, False)]

    form_excluded_columns = [User.user_id]  # Clerk user ID


class ProjectAdmin(ModelView, model=Project):
    """Admin view for Project model."""

    category = "Operational Schema"

    # READ-ONLY MODE - No modifications allowed
    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        Project.project_id,
        Project.name_short,
        Project.name_long,
        Project.project_type_id,
        Project.project_status_type_id,
        Project.cod,
    ]
    column_searchable_list = [Project.name_short, Project.name_long]
    column_sortable_list = [
        Project.project_id,
        Project.name_short,
        Project.cod,
    ]
    column_default_sort = [(Project.name_short, False)]

    form_excluded_columns = [Project.project_id]  # Auto-generated UUID


class ProjectTypeAdmin(ModelView, model=ProjectType):
    """Admin view for ProjectType model."""

    category = "Operational Schema"

    # READ-ONLY MODE - No modifications allowed
    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        ProjectType.project_type_id,
        ProjectType.name_short,
        ProjectType.name_long,
    ]
    column_searchable_list = [ProjectType.name_short, ProjectType.name_long]
    column_sortable_list = [ProjectType.project_type_id, ProjectType.name_short]
    column_default_sort = [(ProjectType.name_short, False)]


class DeviceAdmin(ModelView, model=Device):
    """Admin view for Device model."""

    category = "Project Schema"

    # READ-ONLY MODE - No modifications allowed
    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        Device.device_id,
        Device.name_short,
        Device.name_long,
        Device.device_type,
        Device.logical,
    ]
    column_searchable_list = [Device.name_short, Device.name_long]
    column_sortable_list = [
        Device.device_id,
        Device.name_short,
        Device.device_type_id,
    ]
    column_default_sort = [(Device.device_id, False)]

    form_excluded_columns = [Device.device_id]  # Auto-generated


class SensorTypeAdmin(ModelView, model=SensorType):
    """Admin view for SensorType model."""

    category = "Operational Schema"

    # READ-ONLY MODE - No modifications allowed
    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        SensorType.sensor_type_id,
        SensorType.name_short,
        SensorType.name_long,
    ]
    column_searchable_list = [SensorType.name_short, SensorType.name_long]
    column_sortable_list = [
        SensorType.sensor_type_id,
        SensorType.name_short,
    ]
    column_default_sort = [(SensorType.name_short, False)]


class DeviceModelAdmin(ModelView, model=DeviceModel):
    """Admin view for DeviceModel model."""

    # Permissions
    can_delete = False

    # Metadata
    name = "Device Model"
    name_plural = "Device Models"
    category = "Operational Schema"

    # List page
    column_list = "__all__"
    column_searchable_list = [DeviceModel.brand, DeviceModel.model]
    column_sortable_list = [c for c in DeviceModel.__table__.columns]
    column_default_sort = [(DeviceModel.device_model_id, False)]

    # Form options
    form_excluded_columns = [DeviceModel.device_model_id]  # Auto-generated


class TagAdmin(ModelView, model=Tag):
    """Admin view for Tag model."""

    category = "Project Schema"

    # READ-ONLY MODE - No modifications allowed
    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        Tag.tag_id,
        Tag.name_short,
        Tag.name_long,
        Tag.name_scada,
        Tag.device_id,
        Tag.sensor_type,
        Tag.in_tsdb,
    ]
    column_searchable_list = [Tag.name_short, Tag.name_long, Tag.name_scada]
    column_sortable_list = [
        Tag.tag_id,
        Tag.name_short,
        Tag.device_id,
        Tag.sensor_type_id,
    ]
    column_default_sort = [(Tag.tag_id, False)]

    form_excluded_columns = [Tag.tag_id]  # Auto-generated


class KPIInstanceAdmin(ModelView, model=KPIInstance):
    """Admin view for KPIInstance model."""

    name = "KPI Instance"
    name_plural = "KPI Instances"

    category = "Operational Schema"

    can_create = True
    can_edit = True
    can_delete = True

    column_list = [
        KPIInstance.project,
        KPIInstance.kpi_type,
        KPIInstance.is_visible,
    ]
    column_searchable_list = [KPIInstance.project_id, KPIInstance.kpi_type_id]
    column_sortable_list = [KPIInstance.project_id, KPIInstance.kpi_type_id]
    column_default_sort = [(KPIInstance.project_id, False)]

    form_excluded_columns = [KPIInstance.project_id, KPIInstance.kpi_type_id]


class EventAdmin(ModelView, model=Event):
    """Admin view for Event model."""

    category = "Project Schema"

    # READ-ONLY MODE - No modifications allowed
    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        Event.event_id,
        Event.device_id,
        Event.failure_mode_id,
        Event.root_cause_id,
        Event.time_start,
        Event.time_end,
        Event.time_detected,
        Event.loss_total_financial,
    ]
    column_sortable_list = [
        Event.event_id,
        Event.device_id,
        Event.time_start,
        Event.time_end,
    ]
    column_default_sort = [(Event.time_start, True)]

    form_excluded_columns = [Event.event_id]  # Auto-generated


def setup_admin_views(admin: Admin) -> None:
    """Set up all admin views for core models."""
    # Core business models
    admin.add_view(CompanyAdmin)
    admin.add_view(UserAdmin)
    admin.add_view(ProjectAdmin)
    admin.add_view(ProjectTypeAdmin)

    # Device and sensor models
    admin.add_view(DeviceAdmin)
    admin.add_view(DeviceModelAdmin)
    admin.add_view(SensorTypeAdmin)
    admin.add_view(TagAdmin)
    admin.add_view(KPIInstanceAdmin)

    # Data models (with performance considerations)

    # Event models
    admin.add_view(EventAdmin)
