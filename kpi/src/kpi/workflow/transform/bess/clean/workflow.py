from kpi.workflow.transform.bess.clean.device_attribute import (
    TransformBessCleanDeviceAttribute,
)
from kpi.workflow.transform.bess.clean.event import TransformBessCleanEvent
from kpi.workflow.transform.bess.clean.project_attribute import (
    TransformBessCleanProjectAttribute,
)
from kpi.workflow.transform.bess.clean.sensor import TransformBessCleanSensor


class TransformBessClean(
    TransformBessCleanSensor,
    TransformBessCleanProjectAttribute,
    TransformBessCleanEvent,
    TransformBessCleanDeviceAttribute,
):
    pass
