from core.enumerations import DeviceType


def coord(device_type: DeviceType) -> str:
    return device_type.name.lower()
