from kpi.registry.transform.bess.clean.device_attribute import (
    TransformBessCleanDeviceAttribute,
)
from kpi.registry.transform.bess.clean.event import TransformBessCleanEvent
from kpi.registry.transform.bess.clean.project_attribute import (
    TransformBessCleanProjectAttribute,
)
from kpi.registry.transform.bess.clean.sensor import TransformBessCleanSensor


class TransformBessClean(
    TransformBessCleanSensor,
    TransformBessCleanProjectAttribute,
    TransformBessCleanEvent,
    TransformBessCleanDeviceAttribute,
):
    pass
