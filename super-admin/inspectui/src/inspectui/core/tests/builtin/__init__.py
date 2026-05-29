"""Built-in tests for data validation."""

from inspectui.core.tests.builtin.device_count import (
    ParentDeviceTypeAllowlistTest,
    RequiredDeviceModelsTest,
    RequiredDeviceTypesTest,
    SensorTypeUniquePerDeviceTest,
)

__all__ = [
    "ParentDeviceTypeAllowlistTest",
    "RequiredDeviceModelsTest",
    "RequiredDeviceTypesTest",
    "SensorTypeUniquePerDeviceTest",
]
