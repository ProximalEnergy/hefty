import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from typing import Annotated, Any, cast
from xml.etree import ElementTree as ET

import pandas as pd
from core.db_query import DbQuery, OutputType
from core.enumerations import DeviceTypeEnum, ProjectTypeEnum
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.base import BaseGeometry
from sqlalchemy import select

from app import dependencies, interfaces, utils
from core import models

COLLADA_NS = "http://www.collada.org/2008/03/COLLADASchema"
PV_NS = "http://www.example.com/pvcollada"
PROXIMAL_NS = "https://app.proximal.energy/pvcollada-2.0-extensions"
PVCOLLADA_PROFILE = "PVCollada-2.0"
PROXIMAL_PROFILE = "PVCollada-2.0-Proximal"
DEFAULT_MODULE_DEPTH_MM = 0.0

ET.register_namespace("", COLLADA_NS)
ET.register_namespace("pv", PV_NS)
ET.register_namespace("prox", PROXIMAL_NS)

router = APIRouter(
    prefix="/pvcollada",
    tags=["pvcollada"],
    include_in_schema=utils.get_include_in_schema(),
)


@dataclass(frozen=True)
class PVColladaDevice:
    """Device data needed to export a project structure."""

    device_id: int
    device_id_path: str | None
    device_type_id: int
    device_type_name_short: str | None
    device_type_name_long: str | None
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
    capacity_energy_dc: float | None
    capacity_power_ac_kw: float | None
    capacity_power_dc_kw: float | None
    capacity_energy_dc_kwh: float | None
    modules_per_pv_source_circuit: int | None
    modules_per_combiner: int | None
    point: object | None
    polygon: object | None
    serial_number: str | None


@dataclass(frozen=True)
class PVColladaModule:
    """PV module product data for official PVCollada components."""

    module_id: int
    manufacturer: str | None
    name: str
    module_type: str
    nom_power_w: float
    length_mm: float
    width_mm: float
    depth_mm: float
    num_cells_series: int | None
    num_strings: int | None


@dataclass(frozen=True)
class PVColladaInverter:
    """PV inverter product data for official PVCollada components."""

    inverter_id: str
    manufacturer: str | None
    name: str
    inverter_type: str
    nom_power_ac_w: float
    nom_power_dc_w: float


@dataclass(frozen=True)
class PVColladaComponents:
    """Official PVCollada component models."""

    modules: list[PVColladaModule]
    inverters: list[PVColladaInverter]


@dataclass(frozen=True)
class LocalProjection:
    """Project-local ENU projection metadata."""

    epsg_code: str
    transformer: Transformer
    origin_easting: float
    origin_northing: float


@dataclass(frozen=True)
class ProjectGeometry:
    """Official COLLADA geometry derived from project/device polygons."""

    projection: LocalProjection | None
    boundary: BaseGeometry | None
    rack_devices: dict[int, BaseGeometry]


def _collada_tag(*, name: str) -> str:
    """Return a namespaced COLLADA tag.

    Args:
        name: Local element name.
    """
    return f"{{{COLLADA_NS}}}{name}"


def _pv_tag(*, name: str) -> str:
    """Return a namespaced PVCollada tag.

    Args:
        name: Local element name.
    """
    return f"{{{PV_NS}}}{name}"


def _proximal_tag(*, name: str) -> str:
    """Return a namespaced Proximal extension tag.

    Args:
        name: Local element name.
    """
    return f"{{{PROXIMAL_NS}}}{name}"


def _safe_xml_id(prefix: str, value: object) -> str:
    """Build an XML ID-compatible identifier.

    Args:
        prefix: Identifier prefix.
        value: Value to include in the identifier.
    """
    cleaned = "".join(
        char if char.isalnum() or char in {"_", "-", "."} else "_"
        for char in str(value)
    )
    return f"{prefix}_{cleaned}"


def _add_text(parent: ET.Element, tag: str, value: object | None) -> ET.Element:
    """Append a text element when the value exists.

    Args:
        parent: Parent XML element.
        tag: Child tag name.
        value: Value to serialize.
    """
    element = ET.SubElement(parent, tag)
    if value is not None:
        element.text = str(value)
    return element


def _format_number(*, value: float | int | None) -> str | None:
    """Format a numeric XML value without noisy trailing zeros.

    Args:
        value: Number to format.
    """
    if value is None:
        return None
    return f"{value:g}"


def _dump_geometry_json(*, geometry: object | None) -> str | None:
    """Serialize a GeoAlchemy geometry as compact GeoJSON.

    Args:
        geometry: Geometry value from a model.
    """
    if geometry is None:
        return None
    converted = interfaces.convert(WKBElement=geometry)
    if converted is None:
        return None
    return json.dumps(converted, separators=(",", ":"))


def _scalar_or_none(*, value: Any) -> Any | None:
    """Normalize pandas missing values to None.

    Args:
        value: Dataframe scalar.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return value
    return value


def _optional_int(*, value: Any) -> int | None:
    """Return an int when a dataframe value exists.

    Args:
        value: Dataframe scalar.
    """
    normalized = _scalar_or_none(value=value)
    return int(normalized) if normalized is not None else None


def _optional_float(*, value: Any) -> float | None:
    """Return a float when a dataframe value exists.

    Args:
        value: Dataframe scalar.
    """
    normalized = _scalar_or_none(value=value)
    return float(normalized) if normalized is not None else None


def _optional_str(*, value: Any) -> str | None:
    """Return a string when a dataframe value exists.

    Args:
        value: Dataframe scalar.
    """
    normalized = _scalar_or_none(value=value)
    return str(normalized) if normalized is not None else None


def _mw_to_w(*, value: float | None) -> float | None:
    """Convert MW to W.

    Args:
        value: Power in MW.
    """
    return value * 1_000_000 if value is not None else None


def _meters_to_mm(*, value: float | None) -> float | None:
    """Convert meters to millimeters.

    Args:
        value: Length in meters.
    """
    return value * 1_000 if value is not None else None


def _format_float_list(*, values: list[float]) -> str:
    """Format a COLLADA float list.

    Args:
        values: Floating point values.
    """
    return " ".join(_format_number(value=value) or "0" for value in values)


def _get_utm_epsg_code(*, longitude: float, latitude: float) -> str:
    """Return the WGS84 UTM EPSG code for a coordinate.

    Args:
        longitude: Longitude in degrees.
        latitude: Latitude in degrees.
    """
    zone = math.floor((longitude + 180) / 6) + 1
    epsg = 32600 + zone if latitude >= 0 else 32700 + zone
    return f"EPSG:{epsg}"


def _build_local_projection(
    *,
    project: interfaces.ProjectInterface,
) -> LocalProjection | None:
    """Create a local ENU projection from the project origin.

    Args:
        project: Project payload to export.
    """
    coordinates = _get_project_coordinates(project=project)
    if coordinates is None:
        return None
    longitude, latitude = coordinates
    epsg_code = _get_utm_epsg_code(longitude=longitude, latitude=latitude)
    transformer = Transformer.from_crs("EPSG:4326", epsg_code, always_xy=True)
    origin_easting, origin_northing = transformer.transform(longitude, latitude)
    return LocalProjection(
        epsg_code=epsg_code,
        transformer=transformer,
        origin_easting=origin_easting,
        origin_northing=origin_northing,
    )


def _geometry_to_shape(*, geometry: object | None) -> BaseGeometry | None:
    """Convert a database geometry value into a Shapely geometry.

    Args:
        geometry: Geometry value from a model or interface.
    """
    if geometry is None:
        return None
    converted = interfaces.convert(WKBElement=geometry)
    if converted is None:
        return None
    return shape(converted)


def _project_polygon_to_shape(
    *,
    project: interfaces.ProjectInterface,
) -> BaseGeometry | None:
    """Convert the project polygon interface into a Shapely geometry.

    Args:
        project: Project payload to export.
    """
    if project.polygon is None:
        return None
    return shape(project.polygon.model_dump())


def _to_local_point(
    *,
    projection: LocalProjection,
    longitude: float,
    latitude: float,
) -> tuple[float, float, float]:
    """Convert WGS84 lon/lat to local ENU meters.

    Args:
        projection: Project-local projection metadata.
        longitude: Longitude in degrees.
        latitude: Latitude in degrees.
    """
    easting, northing = projection.transformer.transform(longitude, latitude)
    return (
        easting - projection.origin_easting,
        northing - projection.origin_northing,
        0.0,
    )


def _geometry_exteriors(
    *,
    geometry: BaseGeometry,
) -> list[list[tuple[float, float]]]:
    """Return exterior rings from polygonal geometry.

    Args:
        geometry: Polygonal geometry.
    """
    if isinstance(geometry, Polygon):
        return [list(geometry.exterior.coords)]
    if isinstance(geometry, MultiPolygon):
        return [list(polygon.exterior.coords) for polygon in geometry.geoms]
    return []


def _axis_azimuth_from_local_points(
    *,
    points: list[tuple[float, float, float]],
) -> float | None:
    """Estimate the dominant axis azimuth from local ENU points.

    Args:
        points: Local ENU polygon points.
    """
    if len(points) < 2:
        return None

    mean_x = sum(point[0] for point in points) / len(points)
    mean_y = sum(point[1] for point in points) / len(points)
    covariance_xx = sum((point[0] - mean_x) ** 2 for point in points)
    covariance_yy = sum((point[1] - mean_y) ** 2 for point in points)
    covariance_xy = sum((point[0] - mean_x) * (point[1] - mean_y) for point in points)
    if covariance_xx == 0 and covariance_yy == 0:
        return None

    # Principal component angle from East. Convert to azimuth clockwise from North.
    axis_angle = 0.5 * math.atan2(
        2 * covariance_xy,
        covariance_xx - covariance_yy,
    )
    azimuth = (90 - math.degrees(axis_angle)) % 180
    if math.isclose(azimuth, 0.0, abs_tol=1e-6):
        return 180.0
    return azimuth


def _build_project_geometry(
    *,
    project: interfaces.ProjectInterface,
    devices: list[PVColladaDevice],
) -> ProjectGeometry:
    """Build official geometry inputs from project and device polygons.

    Args:
        project: Project payload to export.
        devices: Project devices to serialize.
    """
    projection = _build_local_projection(project=project)
    if projection is None:
        return ProjectGeometry(projection=None, boundary=None, rack_devices={})

    rack_devices: dict[int, BaseGeometry] = {}
    for device in devices:
        if device.device_type_id != DeviceTypeEnum.TRACKER_ROW:
            continue
        device_geometry = _geometry_to_shape(geometry=device.polygon)
        if device_geometry is not None:
            rack_devices[device.device_id] = device_geometry

    return ProjectGeometry(
        projection=projection,
        boundary=_project_polygon_to_shape(project=project),
        rack_devices=rack_devices,
    )


def _device_from_record(*, record: dict[str, Any]) -> PVColladaDevice:
    """Build a PVCollada device from a dataframe record.

    Args:
        record: Device dataframe row as a dictionary.
    """
    return PVColladaDevice(
        device_id=int(record["device_id"]),
        device_id_path=_optional_str(value=record["device_id_path"]),
        device_type_id=int(record["device_type_id"]),
        device_type_name_short=_optional_str(value=record["device_type_name_short"]),
        device_type_name_long=_optional_str(value=record["device_type_name_long"]),
        device_model_id=_optional_int(value=record["device_model_id"]),
        cec_pv_inverter_id=_optional_int(value=record["cec_pv_inverter_id"]),
        cec_pv_module_id=_optional_int(value=record["cec_pv_module_id"]),
        pv_module_id=_optional_int(value=record["pv_module_id"]),
        parent_device_id=_optional_int(value=record["parent_device_id"]),
        logical=bool(record["logical"]),
        name_short=_optional_str(value=record["name_short"]),
        name_long=_optional_str(value=record["name_long"]),
        capacity_dc=_optional_float(value=record["capacity_dc"]),
        capacity_ac=_optional_float(value=record["capacity_ac"]),
        capacity_energy_dc=_optional_float(value=record["capacity_energy_dc"]),
        capacity_power_ac_kw=_optional_float(value=record["capacity_power_ac_kw"]),
        capacity_power_dc_kw=_optional_float(value=record["capacity_power_dc_kw"]),
        capacity_energy_dc_kwh=_optional_float(value=record["capacity_energy_dc_kwh"]),
        modules_per_pv_source_circuit=_optional_int(
            value=record["modules_per_pv_source_circuit"]
        ),
        modules_per_combiner=_optional_int(value=record["modules_per_combiner"]),
        point=_scalar_or_none(value=record["point"]),
        polygon=_scalar_or_none(value=record["polygon"]),
        serial_number=_optional_str(value=record["serial_number"]),
    )


async def _get_project_devices(*, project_name_short: str) -> list[PVColladaDevice]:
    """Fetch project devices as tabular data.

    Args:
        project_name_short: Project schema name.
    """
    stmt = (
        select(
            models.Device.device_id,
            models.Device.device_id_path,
            models.Device.device_type_id,
            models.DeviceType.name_short.label("device_type_name_short"),
            models.DeviceType.name_long.label("device_type_name_long"),
            models.Device.device_model_id,
            models.Device.cec_pv_inverter_id,
            models.Device.cec_pv_module_id,
            models.Device.pv_module_id,
            models.Device.parent_device_id,
            models.Device.logical,
            models.Device.name_short,
            models.Device.name_long,
            models.Device.capacity_dc,
            models.Device.capacity_ac,
            models.Device.capacity_energy_dc,
            models.Device.capacity_power_ac_kw,
            models.Device.capacity_power_dc_kw,
            models.Device.capacity_energy_dc_kwh,
            models.PVDCCombiner.modules_per_pv_source_circuit,
            models.PVDCCombiner.modules_per_combiner,
            models.Device.point,
            models.Device.polygon,
            models.Device.serial_number,
        )
        .outerjoin(
            models.DeviceType,
            models.Device.device_type_id == models.DeviceType.device_type_id,
        )
        .outerjoin(
            models.PVDCCombiner,
            models.Device.device_id == models.PVDCCombiner.device_id,
        )
        .order_by(models.Device.device_id_path, models.Device.device_id)
    )
    devices_df = await DbQuery(query=stmt).get_async(
        output_type=OutputType.PANDAS,
        schema=project_name_short,
    )
    records = cast(
        list[dict[str, Any]],
        devices_df.to_dict(orient="records"),
    )
    return [_device_from_record(record=record) for record in records]


def _module_type_from_bifaciality(*, bifaciality_factor: float | None) -> str:
    """Map module bifaciality to PVCollada module type.

    Args:
        bifaciality_factor: Module bifaciality factor.
    """
    return "bifacial" if bifaciality_factor and bifaciality_factor > 0 else "monofacial"


def _module_from_record(*, record: dict[str, Any]) -> PVColladaModule:
    """Build official module data from a dataframe record.

    Args:
        record: Module dataframe row as a dictionary.
    """
    cells_in_series = _optional_int(value=record["cells_in_series"])
    cells_in_parallel = _optional_int(value=record["cells_in_parallel"])
    length_mm = _meters_to_mm(value=_optional_float(value=record["length"]))
    width_mm = _meters_to_mm(value=_optional_float(value=record["width"]))
    return PVColladaModule(
        module_id=int(record["pv_module_id"]),
        manufacturer=_optional_str(value=record["manufacturer"]),
        name=_optional_str(value=record["model"]) or f"Module {record['pv_module_id']}",
        module_type=_module_type_from_bifaciality(
            bifaciality_factor=_optional_float(value=record["bifaciality_factor"]),
        ),
        nom_power_w=_optional_float(value=record["pmax"]) or 0.0,
        length_mm=length_mm or 0.0,
        width_mm=width_mm or 0.0,
        depth_mm=DEFAULT_MODULE_DEPTH_MM,
        num_cells_series=cells_in_series,
        num_strings=cells_in_parallel,
    )


async def _get_modules(*, module_ids: set[int]) -> list[PVColladaModule]:
    """Fetch official PV module component data.

    Args:
        module_ids: Operational PV module IDs used by project devices.
    """
    if not module_ids:
        return []

    stmt = (
        select(
            models.PVModule.pv_module_id,
            models.PVModule.manufacturer,
            models.PVModule.model,
            models.PVModule.bifaciality_factor,
            models.PVModule.pmax,
            models.PVModule.length,
            models.PVModule.width,
            models.PVModule.cells_in_series,
            models.PVModule.cells_in_parallel,
        )
        .where(models.PVModule.pv_module_id.in_(module_ids))
        .order_by(models.PVModule.pv_module_id)
    )
    modules_df = await DbQuery(query=stmt).get_async(
        output_type=OutputType.PANDAS,
    )
    records = cast(
        list[dict[str, Any]],
        modules_df.to_dict(orient="records"),
    )
    return [_module_from_record(record=record) for record in records]


async def _get_device_model_labels(
    *,
    device_model_ids: set[int],
) -> dict[int, tuple[str | None, str | None]]:
    """Fetch device model brand/name labels.

    Args:
        device_model_ids: Device model IDs used by inverter devices.
    """
    if not device_model_ids:
        return {}

    stmt = (
        select(
            models.DeviceModel.device_model_id,
            models.DeviceModel.brand,
            models.DeviceModel.model,
        )
        .where(models.DeviceModel.device_model_id.in_(device_model_ids))
        .order_by(models.DeviceModel.device_model_id)
    )
    device_models_df = await DbQuery(query=stmt).get_async(
        output_type=OutputType.PANDAS,
    )
    return {
        int(record["device_model_id"]): (
            _optional_str(value=record["brand"]),
            _optional_str(value=record["model"]),
        )
        for record in device_models_df.to_dict(orient="records")
    }


async def _get_cec_inverter_labels(
    *,
    cec_inverter_ids: set[int],
) -> dict[int, tuple[str | None, str | None, float | None]]:
    """Fetch CEC inverter labels and AC ratings.

    Args:
        cec_inverter_ids: CEC inverter IDs used by inverter devices.
    """
    if not cec_inverter_ids:
        return {}

    stmt = (
        select(
            models.CECPVInverter.cec_pv_inverter_id,
            models.CECPVInverter.manufacturer,
            models.CECPVInverter.model_number,
            models.CECPVInverter.max_output_power_unity_pf,
        )
        .where(models.CECPVInverter.cec_pv_inverter_id.in_(cec_inverter_ids))
        .order_by(models.CECPVInverter.cec_pv_inverter_id)
    )
    cec_inverters_df = await DbQuery(query=stmt).get_async(
        output_type=OutputType.PANDAS,
    )
    return {
        int(record["cec_pv_inverter_id"]): (
            _optional_str(value=record["manufacturer"]),
            _optional_str(value=record["model_number"]),
            _optional_float(value=record["max_output_power_unity_pf"]),
        )
        for record in cec_inverters_df.to_dict(orient="records")
    }


async def _get_components(
    *,
    devices: list[PVColladaDevice],
) -> PVColladaComponents:
    """Fetch official PVCollada component models used by devices.

    Args:
        devices: Project devices to serialize.
    """
    module_ids = {device.pv_module_id for device in devices if device.pv_module_id}
    inverter_devices = [
        device
        for device in devices
        if device.device_type_id == DeviceTypeEnum.PV_INVERTER
    ]
    device_model_ids = {
        device.device_model_id for device in inverter_devices if device.device_model_id
    }
    cec_inverter_ids = {
        device.cec_pv_inverter_id
        for device in inverter_devices
        if device.cec_pv_inverter_id
    }

    modules = await _get_modules(module_ids=cast(set[int], module_ids))
    device_model_labels = await _get_device_model_labels(
        device_model_ids=cast(set[int], device_model_ids),
    )
    cec_inverter_labels = await _get_cec_inverter_labels(
        cec_inverter_ids=cast(set[int], cec_inverter_ids),
    )

    inverters: list[PVColladaInverter] = []
    for device in inverter_devices:
        manufacturer: str | None = None
        name: str | None = None
        ac_rating_w: float | None = None

        if device.cec_pv_inverter_id in cec_inverter_labels:
            manufacturer, name, ac_rating_w = cec_inverter_labels[
                cast(int, device.cec_pv_inverter_id)
            ]
        elif device.device_model_id in device_model_labels:
            manufacturer, name = device_model_labels[cast(int, device.device_model_id)]

        ac_power_w = ac_rating_w or _mw_to_w(value=device.capacity_ac) or 0.0
        dc_power_w = _mw_to_w(value=device.capacity_dc) or ac_power_w
        inverters.append(
            PVColladaInverter(
                inverter_id=_safe_xml_id("inverter_model", device.device_id),
                manufacturer=manufacturer,
                name=name or device.name_long or f"Inverter {device.device_id}",
                inverter_type="central",
                nom_power_ac_w=ac_power_w,
                nom_power_dc_w=dc_power_w,
            )
        )

    return PVColladaComponents(modules=modules, inverters=inverters)


def _get_project_coordinates(
    *,
    project: interfaces.ProjectInterface,
) -> tuple[float, float] | None:
    """Return project longitude and latitude when available.

    Args:
        project: Project payload from the API dependency.
    """
    if project.point is None or len(project.point.coordinates) < 2:
        return None
    longitude, latitude = project.point.coordinates[:2]
    return longitude, latitude


def _estimate_module_count(*, devices: list[PVColladaDevice]) -> int | None:
    """Estimate module count from DC combiner metadata.

    Args:
        devices: Project devices to serialize.
    """
    count = sum(
        device.modules_per_combiner or 0
        for device in devices
        if device.device_type_id == DeviceTypeEnum.PV_DC_COMBINER
    )
    return count or None


def _estimate_string_count(*, devices: list[PVColladaDevice]) -> int | None:
    """Estimate string count from DC combiner metadata.

    Args:
        devices: Project devices to serialize.
    """
    count = 0
    for device in devices:
        if device.device_type_id != DeviceTypeEnum.PV_DC_COMBINER:
            continue
        modules_per_combiner = device.modules_per_combiner
        modules_per_source = device.modules_per_pv_source_circuit
        if not modules_per_combiner or not modules_per_source:
            continue
        count += modules_per_combiner // modules_per_source
    return count or None


def _add_components(
    *,
    parent: ET.Element,
    components: PVColladaComponents,
) -> None:
    """Add official PVCollada component models.

    Args:
        parent: Parent PVCollada technique element.
        components: Official component data.
    """
    if not components.modules and not components.inverters:
        return

    components_element = ET.SubElement(parent, _pv_tag(name="components"))
    if components.modules:
        modules_element = ET.SubElement(components_element, _pv_tag(name="modules"))
        for module in components.modules:
            module_element = ET.SubElement(
                modules_element,
                _pv_tag(name="module"),
                id=_safe_xml_id("module", module.module_id),
            )
            _add_text(module_element, _pv_tag(name="manufacturer"), module.manufacturer)
            _add_text(module_element, _pv_tag(name="name"), module.name)
            _add_text(module_element, _pv_tag(name="module_type"), module.module_type)
            _add_text(module_element, _pv_tag(name="nom_power"), module.nom_power_w)
            _add_text(module_element, _pv_tag(name="length"), module.length_mm)
            _add_text(module_element, _pv_tag(name="width"), module.width_mm)
            _add_text(module_element, _pv_tag(name="depth"), module.depth_mm)
            _add_text(
                module_element,
                _pv_tag(name="num_cells_series"),
                module.num_cells_series,
            )
            _add_text(module_element, _pv_tag(name="num_strings"), module.num_strings)

    if components.inverters:
        inverters_element = ET.SubElement(components_element, _pv_tag(name="inverters"))
        for inverter in components.inverters:
            inverter_element = ET.SubElement(
                inverters_element,
                _pv_tag(name="inverter"),
                id=inverter.inverter_id,
            )
            _add_text(
                inverter_element, _pv_tag(name="manufacturer"), inverter.manufacturer
            )
            _add_text(inverter_element, _pv_tag(name="name"), inverter.name)
            _add_text(
                inverter_element,
                _pv_tag(name="inverter_type"),
                inverter.inverter_type,
            )
            _add_text(
                inverter_element,
                _pv_tag(name="nom_power_ac"),
                inverter.nom_power_ac_w,
            )
            _add_text(
                inverter_element,
                _pv_tag(name="nom_power_dc"),
                inverter.nom_power_dc_w,
            )


def _add_asset(
    *,
    root: ET.Element,
    project: interfaces.ProjectInterface,
    devices: list[PVColladaDevice],
    components: PVColladaComponents,
    project_geometry: ProjectGeometry,
    generated_at: datetime,
) -> None:
    """Add COLLADA asset metadata with PVCollada project details.

    Args:
        root: Root COLLADA element.
        project: Project payload to export.
        devices: Project devices to serialize.
        components: Official component data.
        project_geometry: Official geometry derived from project/device polygons.
        generated_at: Timestamp used for created/modified fields.
    """
    asset = ET.SubElement(root, _collada_tag(name="asset"))
    contributor = ET.SubElement(asset, _collada_tag(name="contributor"))
    _add_text(contributor, _collada_tag(name="author"), "Proximal Energy")
    _add_text(
        contributor,
        _collada_tag(name="comments"),
        "PVCollada 2.0 export of the Proximal project structure.",
    )

    coordinates = _get_project_coordinates(project=project)
    if coordinates is not None:
        longitude, latitude = coordinates
        coverage = ET.SubElement(asset, _collada_tag(name="coverage"))
        location = ET.SubElement(coverage, _collada_tag(name="geographic_location"))
        _add_text(
            location, _collada_tag(name="longitude"), _format_number(value=longitude)
        )
        _add_text(
            location, _collada_tag(name="latitude"), _format_number(value=latitude)
        )
        altitude = ET.SubElement(
            location, _collada_tag(name="altitude"), mode="absolute"
        )
        altitude.text = _format_number(value=project.elevation) or "0"

    generated_at_text = generated_at.isoformat().replace("+00:00", "Z")
    _add_text(asset, _collada_tag(name="created"), generated_at_text)
    _add_text(asset, _collada_tag(name="modified"), generated_at_text)
    ET.SubElement(asset, _collada_tag(name="unit"), meter="1", name="m")
    _add_text(asset, _collada_tag(name="up_axis"), "Z_UP")

    extra = ET.SubElement(asset, _collada_tag(name="extra"))
    pv_technique = ET.SubElement(
        extra,
        _collada_tag(name="technique"),
        profile=PVCOLLADA_PROFILE,
    )
    software = ET.SubElement(pv_technique, _pv_tag(name="software"))
    _add_text(software, _pv_tag(name="source"), "Proximal Energy Platform")
    _add_text(software, _pv_tag(name="target"), "PVCollada 2.0")

    pv_project = ET.SubElement(pv_technique, _pv_tag(name="project"))
    _add_text(pv_project, _pv_tag(name="name"), project.name_long)
    _add_text(pv_project, _pv_tag(name="drawing"), project.name_short)
    _add_text(pv_project, _pv_tag(name="company"), "Proximal Energy")
    _add_text(pv_project, _pv_tag(name="timezone"), project.time_zone)
    if project_geometry.projection is not None:
        _add_text(
            pv_project,
            _pv_tag(name="local_projection"),
            project_geometry.projection.epsg_code,
        )
    if project_geometry.boundary is not None:
        _add_text(
            pv_project,
            _pv_tag(name="boundary"),
            "ProjectStructure/ProjectBoundary/project_boundary_instance",
        )
    _add_text(
        pv_project,
        _pv_tag(name="module_count"),
        _estimate_module_count(devices=devices),
    )
    _add_text(
        pv_project,
        _pv_tag(name="table_count"),
        len(project_geometry.rack_devices) or None,
    )
    _add_text(
        pv_project,
        _pv_tag(name="string_count"),
        _estimate_string_count(devices=devices),
    )
    _add_text(
        pv_project, _pv_tag(name="capacity_dc"), _mw_to_w(value=project.capacity_dc)
    )
    _add_text(
        pv_project, _pv_tag(name="capacity_ac"), _mw_to_w(value=project.capacity_ac)
    )
    _add_text(
        pv_project,
        _pv_tag(name="interconnection_limit"),
        _mw_to_w(value=project.poi),
    )

    _add_components(parent=pv_technique, components=components)

    proximal_technique = ET.SubElement(
        extra,
        _collada_tag(name="technique"),
        profile=PROXIMAL_PROFILE,
    )
    proximal_project = ET.SubElement(proximal_technique, _proximal_tag(name="project"))
    project_fields: dict[str, object | None] = {
        "project_id": project.project_id,
        "project_type_id": project.project_type_id,
        "name_short": project.name_short,
        "name_long": project.name_long,
        "address": project.address,
        "time_zone": project.time_zone,
        "poi_mw": project.poi,
        "capacity_dc_mw": project.capacity_dc,
        "capacity_ac_mw": project.capacity_ac,
        "capacity_bess_power_ac_mw": project.capacity_bess_power_ac,
        "capacity_bess_energy_bol_dc_mwh": project.capacity_bess_energy_bol_dc,
        "point_geojson": project.point.model_dump_json(),
        "polygon_geojson": (
            project.polygon.model_dump_json() if project.polygon else None
        ),
        "cod": project.cod,
    }
    for key, value in project_fields.items():
        _add_text(proximal_project, _proximal_tag(name=key), value)


def _add_device_extra(
    *,
    node: ET.Element,
    device: PVColladaDevice,
    is_table: bool,
) -> None:
    """Add Proximal device metadata to a scene node.

    Args:
        node: COLLADA node that represents the device.
        device: Project device model.
        is_table: Whether to add an official PVCollada table tag.
    """
    extra = ET.SubElement(node, _collada_tag(name="extra"))
    if is_table:
        pv_technique = ET.SubElement(
            extra,
            _collada_tag(name="technique"),
            profile=PVCOLLADA_PROFILE,
        )
        table = ET.SubElement(pv_technique, _pv_tag(name="table"))
        _add_text(table, _pv_tag(name="type"), "tracker")

    technique = ET.SubElement(
        extra,
        _collada_tag(name="technique"),
        profile=PROXIMAL_PROFILE,
    )
    device_element = ET.SubElement(
        technique,
        _proximal_tag(name="device"),
        id=_safe_xml_id("device_metadata", device.device_id),
    )

    fields: dict[str, object | None] = {
        "device_id": device.device_id,
        "device_id_path": device.device_id_path,
        "parent_device_id": device.parent_device_id,
        "device_type_id": device.device_type_id,
        "device_type_name_short": device.device_type_name_short,
        "device_type_name_long": device.device_type_name_long,
        "device_model_id": device.device_model_id,
        "cec_pv_inverter_id": device.cec_pv_inverter_id,
        "cec_pv_module_id": device.cec_pv_module_id,
        "pv_module_id": device.pv_module_id,
        "logical": device.logical,
        "name_short": device.name_short,
        "name_long": device.name_long,
        "capacity_dc_mw": device.capacity_dc,
        "capacity_ac_mw": device.capacity_ac,
        "capacity_energy_dc_mwh": device.capacity_energy_dc,
        "capacity_power_ac_kw": device.capacity_power_ac_kw,
        "capacity_power_dc_kw": device.capacity_power_dc_kw,
        "capacity_energy_dc_kwh": device.capacity_energy_dc_kwh,
        "modules_per_pv_source_circuit": device.modules_per_pv_source_circuit,
        "modules_per_combiner": device.modules_per_combiner,
        "point_geojson": _dump_geometry_json(geometry=device.point),
        "polygon_geojson": _dump_geometry_json(geometry=device.polygon),
        "serial_number": device.serial_number,
    }
    for key, value in fields.items():
        _add_text(device_element, _proximal_tag(name=key), value)


def _add_device_node(
    *,
    parent: ET.Element,
    device: PVColladaDevice,
    children_by_parent_id: dict[int | None, list[PVColladaDevice]],
    project_geometry: ProjectGeometry,
    rack_device_ids: set[int],
) -> None:
    """Add a device and its descendants as COLLADA scene nodes.

    Args:
        parent: Parent XML element.
        device: Device to serialize.
        children_by_parent_id: Mapping from parent device id to child devices.
        project_geometry: Official geometry derived from project/device polygons.
        rack_device_ids: Devices with official rack geometry and module metadata.
    """
    label = device.name_long or device.name_short or f"Device {device.device_id}"
    node = ET.SubElement(
        parent,
        _collada_tag(name="node"),
        id=_safe_xml_id("device", device.device_id),
        name=label,
        sid=_safe_xml_id("device", device.device_id),
    )

    is_rack_device = device.device_id in rack_device_ids
    if is_rack_device:
        instance_geometry = ET.SubElement(
            node,
            _collada_tag(name="instance_geometry"),
            url=f"#{_safe_xml_id('rack_geometry', device.device_id)}",
        )
        instance_extra = ET.SubElement(instance_geometry, _collada_tag(name="extra"))
        instance_technique = ET.SubElement(
            instance_extra,
            _collada_tag(name="technique"),
            profile=PVCOLLADA_PROFILE,
        )
        ET.SubElement(
            instance_technique,
            _pv_tag(name="instance_rack"),
            id=_safe_xml_id("rack_instance", device.device_id),
        )

    for child in children_by_parent_id.get(device.device_id, []):
        _add_device_node(
            parent=node,
            device=child,
            children_by_parent_id=children_by_parent_id,
            project_geometry=project_geometry,
            rack_device_ids=rack_device_ids,
        )

    _add_device_extra(node=node, device=device, is_table=is_rack_device)


def _sort_devices(*, devices: list[PVColladaDevice]) -> list[PVColladaDevice]:
    """Sort devices by hierarchy path and name.

    Args:
        devices: Devices to sort.
    """
    return sorted(
        devices,
        key=lambda device: (
            device.device_id_path or "",
            device.name_short or "",
            device.device_id,
        ),
    )


def _polygon_vertices(
    *,
    geometry: BaseGeometry,
    projection: LocalProjection,
) -> tuple[list[tuple[float, float, float]], list[list[int]]]:
    """Convert polygon exteriors to local COLLADA vertices.

    Args:
        geometry: Polygonal geometry.
        projection: Project-local projection metadata.
    """
    vertices: list[tuple[float, float, float]] = []
    polygons: list[list[int]] = []
    for ring in _geometry_exteriors(geometry=geometry):
        if len(ring) < 4:
            continue
        indices: list[int] = []
        for longitude, latitude in ring[:-1]:
            indices.append(len(vertices))
            vertices.append(
                _to_local_point(
                    projection=projection,
                    longitude=longitude,
                    latitude=latitude,
                )
            )
        if len(indices) >= 3:
            polygons.append(indices)
    return vertices, polygons


def _add_mesh_geometry(
    *,
    library_geometries: ET.Element,
    geometry_id: str,
    geometry: BaseGeometry,
    projection: LocalProjection,
    rack_module_id: str | None = None,
) -> None:
    """Add a polygonal COLLADA mesh geometry.

    Args:
        library_geometries: COLLADA library_geometries element.
        geometry_id: Geometry XML id.
        geometry: Polygonal geometry.
        projection: Project-local projection metadata.
        rack_module_id: Optional module id to mark geometry as a PVCollada rack.
    """
    vertices, polygons = _polygon_vertices(geometry=geometry, projection=projection)
    if not vertices or not polygons:
        return

    geometry_element = ET.SubElement(
        library_geometries,
        _collada_tag(name="geometry"),
        id=geometry_id,
    )
    mesh = ET.SubElement(geometry_element, _collada_tag(name="mesh"))
    source_id = f"{geometry_id}_positions"
    float_array_id = f"{geometry_id}_float_array"
    source = ET.SubElement(mesh, _collada_tag(name="source"), id=source_id)
    float_array = ET.SubElement(
        source,
        _collada_tag(name="float_array"),
        id=float_array_id,
        count=str(len(vertices) * 3),
    )
    float_values = [value for vertex in vertices for value in vertex]
    float_array.text = _format_float_list(values=float_values)

    technique_common = ET.SubElement(source, _collada_tag(name="technique_common"))
    accessor = ET.SubElement(
        technique_common,
        _collada_tag(name="accessor"),
        count=str(len(vertices)),
        source=f"#{float_array_id}",
        stride="3",
    )
    ET.SubElement(accessor, _collada_tag(name="param"), name="X", type="float")
    ET.SubElement(accessor, _collada_tag(name="param"), name="Y", type="float")
    ET.SubElement(accessor, _collada_tag(name="param"), name="Z", type="float")

    vertices_id = f"{geometry_id}_vertices"
    vertices_element = ET.SubElement(
        mesh, _collada_tag(name="vertices"), id=vertices_id
    )
    ET.SubElement(
        vertices_element,
        _collada_tag(name="input"),
        semantic="POSITION",
        source=f"#{source_id}",
    )
    polylist = ET.SubElement(
        mesh,
        _collada_tag(name="polylist"),
        count=str(len(polygons)),
    )
    ET.SubElement(
        polylist,
        _collada_tag(name="input"),
        offset="0",
        semantic="VERTEX",
        source=f"#{vertices_id}",
    )
    _add_text(
        polylist,
        _collada_tag(name="vcount"),
        " ".join(str(len(polygon)) for polygon in polygons),
    )
    _add_text(
        polylist,
        _collada_tag(name="p"),
        " ".join(str(index) for polygon in polygons for index in polygon),
    )

    if rack_module_id is not None:
        extra = ET.SubElement(geometry_element, _collada_tag(name="extra"))
        technique = ET.SubElement(
            extra,
            _collada_tag(name="technique"),
            profile=PVCOLLADA_PROFILE,
        )
        rack = ET.SubElement(technique, _pv_tag(name="rack"))
        _add_text(rack, _pv_tag(name="rack_type"), "tracker")
        tracker_azimuth = _axis_azimuth_from_local_points(points=vertices) or 180.0
        _add_text(rack, _pv_tag(name="tracker_azimuth"), tracker_azimuth)
        _add_text(rack, _pv_tag(name="module_id"), rack_module_id)


def _add_library_geometries(
    *,
    root: ET.Element,
    project_geometry: ProjectGeometry,
    components: PVColladaComponents,
    devices: list[PVColladaDevice],
) -> None:
    """Add official geometry library entries.

    Args:
        root: Root COLLADA element.
        project_geometry: Official geometry derived from project/device polygons.
        components: Official component data.
        devices: Project devices to serialize.
    """
    projection = project_geometry.projection
    if projection is None:
        return
    if project_geometry.boundary is None and not project_geometry.rack_devices:
        return

    library_geometries = ET.SubElement(root, _collada_tag(name="library_geometries"))
    if project_geometry.boundary is not None:
        _add_mesh_geometry(
            library_geometries=library_geometries,
            geometry_id="ProjectBoundaryGeometry",
            geometry=project_geometry.boundary,
            projection=projection,
        )

    module_xml_ids = {
        module.module_id: _safe_xml_id("module", module.module_id)
        for module in components.modules
    }
    device_by_id = {device.device_id: device for device in devices}
    for device_id, geometry in project_geometry.rack_devices.items():
        device = device_by_id.get(device_id)
        rack_module_id = (
            module_xml_ids[device.pv_module_id]
            if device is not None and device.pv_module_id in module_xml_ids
            else None
        )
        _add_mesh_geometry(
            library_geometries=library_geometries,
            geometry_id=_safe_xml_id("rack_geometry", device_id),
            geometry=geometry,
            projection=projection,
            rack_module_id=rack_module_id,
        )


def _add_device_scene(
    *,
    root: ET.Element,
    project: interfaces.ProjectInterface,
    devices: list[PVColladaDevice],
    project_geometry: ProjectGeometry,
    components: PVColladaComponents,
) -> None:
    """Add the project device hierarchy to the COLLADA visual scene.

    Args:
        root: Root COLLADA element.
        project: Project payload to export.
        devices: Project devices to serialize.
        project_geometry: Official geometry derived from project/device polygons.
        components: Official component data.
    """
    children_by_parent_id: dict[int | None, list[PVColladaDevice]] = defaultdict(list)
    device_ids = {device.device_id for device in devices}

    for device in _sort_devices(devices=devices):
        parent_id = device.parent_device_id
        if parent_id not in device_ids:
            parent_id = None
        children_by_parent_id[parent_id].append(device)

    rack_device_ids = (
        set(project_geometry.rack_devices) if components.modules else set()
    )

    library_visual_scenes = ET.SubElement(
        root, _collada_tag(name="library_visual_scenes")
    )
    visual_scene = ET.SubElement(
        library_visual_scenes,
        _collada_tag(name="visual_scene"),
        id="VisualSceneModel",
        name=f"{project.name_long} Structure",
    )
    project_node = ET.SubElement(
        visual_scene,
        _collada_tag(name="node"),
        id="ProjectStructure",
        name=project.name_long,
        sid="ProjectStructure",
    )
    if project_geometry.boundary is not None:
        boundary_node = ET.SubElement(
            project_node,
            _collada_tag(name="node"),
            id="ProjectBoundary",
            name="Project Boundary",
            sid="ProjectBoundary",
        )
        ET.SubElement(
            boundary_node,
            _collada_tag(name="instance_geometry"),
            sid="project_boundary_instance",
            url="#ProjectBoundaryGeometry",
        )

    for device in children_by_parent_id.get(None, []):
        _add_device_node(
            parent=project_node,
            device=device,
            children_by_parent_id=children_by_parent_id,
            project_geometry=project_geometry,
            rack_device_ids=rack_device_ids,
        )

    scene = ET.SubElement(root, _collada_tag(name="scene"))
    ET.SubElement(
        scene,
        _collada_tag(name="instance_visual_scene"),
        url="#VisualSceneModel",
    )


def _build_pvcollada_document(
    *,
    project: interfaces.ProjectInterface,
    devices: list[PVColladaDevice],
    components: PVColladaComponents,
    project_geometry: ProjectGeometry,
) -> bytes:
    """Build a PVCollada 2.0 XML document for a project.

    Args:
        project: Project payload to export.
        devices: Project devices to serialize.
        components: Official component data.
        project_geometry: Official geometry derived from project/device polygons.
    """
    generated_at = datetime.now(UTC)
    root = ET.Element(
        _collada_tag(name="COLLADA"),
        {
            "version": "1.5.0",
            "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        },
    )

    _add_asset(
        root=root,
        project=project,
        devices=devices,
        components=components,
        project_geometry=project_geometry,
        generated_at=generated_at,
    )
    _add_library_geometries(
        root=root,
        project_geometry=project_geometry,
        components=components,
        devices=devices,
    )
    _add_device_scene(
        root=root,
        project=project,
        devices=devices,
        project_geometry=project_geometry,
        components=components,
    )
    ET.indent(root, space="  ")

    return cast(
        bytes,
        ET.tostring(root, encoding="utf-8", xml_declaration=True),
    )


@router.get("/export", operation_id="export_project_pvcollada")
async def export_project_pvcollada(
    project: Annotated[
        interfaces.ProjectInterface,
        Depends(dependencies.get_project_api),
    ],
):
    """Export the project device hierarchy as a PVCollada 2.0 file.

    Args:
        project: Project payload from the API dependency.
    """
    if project.project_type_id not in {ProjectTypeEnum.PV, ProjectTypeEnum.PVS}:
        raise HTTPException(
            status_code=400,
            detail=(
                "PVCollada export is only available for PV and PV+Storage projects."
            ),
        )

    devices = await _get_project_devices(project_name_short=project.name_short)
    if not devices:
        raise HTTPException(
            status_code=404,
            detail="No devices found for this project.",
        )

    components = await _get_components(devices=devices)
    project_geometry = _build_project_geometry(project=project, devices=devices)
    xml_bytes = _build_pvcollada_document(
        project=project,
        devices=devices,
        components=components,
        project_geometry=project_geometry,
    )
    filename = f"{project.name_short}_pvcollada_2_0.pvc2"

    return StreamingResponse(
        BytesIO(xml_bytes),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
