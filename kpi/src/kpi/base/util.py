from core.enumerations import DeviceTypeEnum


def coord(device_type: DeviceTypeEnum) -> str:
    return device_type.name.lower()
