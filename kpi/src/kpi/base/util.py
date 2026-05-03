from core.enumerations import DeviceTypeEnum


def coord(device_type: DeviceTypeEnum) -> str:
    return device_type.name.lower()


def reverse_coord(dim: str) -> DeviceTypeEnum:
    return DeviceTypeEnum[dim.upper()]
