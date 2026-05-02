import io
import json
from typing import Annotated

import polars as pl
from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from natsort import natsorted
from pydantic import BaseModel
from shapely.geometry import mapping
from shapely.wkb import loads as wkb_loads
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import custom_types, interfaces, utils
from app._utils.arrow import polars_to_arrow_response
from app.dependencies import (
    check_project_access_async,
    get_project_db,
    get_project_db_async,
)
from app.logger import logger

DESCRIPTION_404 = "Device not found"

router = APIRouter(
    prefix="/devices",
    tags=["project_devices"],
    dependencies=[Depends(check_project_access_async)],
)


class DevicesFilterRequest(BaseModel):
    """Request model for v2 devices endpoint with large filter support"""

    device_ids: list[int] = []
    device_type_ids: list[int] = []
    parent_device_ids: list[int | None] = []
    name_short: str = ""
    name_long: str = ""
    device_id_descendent_of: int | None = None
    deep: bool = False
    with_tags: bool = False
    limit: int | None = None
    offset: int = 0
    format: str = "json"  # "json", "arrow", "parquet"
    fields: Annotated[list[str], Query()] = []


class DeviceSerialNumberUpdate(BaseModel):
    """Request model for updating a project's device serial number."""

    serial_number: str | None = None


@router.get(
    "/{device_id}",
    response_model=interfaces.DeviceInterface,
    operation_id="get_project_device_by_id",
    responses={404: {"description": DESCRIPTION_404}},
)
async def get_project_device_route(
    device_id: int,
    deep: custom_types.AnnotatedDeep = False,
    project_db: AsyncSession = Depends(get_project_db_async),
):
    """Return a single project device with optional relationship data.

    Args:
        device_id: Identifier of the device to fetch.
        deep: Whether to include related entities such as children and tags.
        project_db: Database session for the current project.
    """
    project_schema = await utils.get_project_schema_async(project_db=project_db)
    query_obj = core.crud.project.devices.get_project_device(
        device_id=device_id,
        deep=deep,
    )
    device = await query_obj.get_async(
        output_type=OutputType.SQLALCHEMY,
        schema=project_schema,
    )
    utils.check_404(value=device, detail=DESCRIPTION_404)
    return device


@router.patch(
    "/{device_id}",
    response_model=interfaces.DeviceInterface,
    operation_id="patch_project_device",
    responses={404: {"description": DESCRIPTION_404}},
)
async def patch_project_device_route(
    device_id: int,
    payload: DeviceSerialNumberUpdate,
    project_db: AsyncSession = Depends(get_project_db_async),
):
    """Update editable fields for a project device.

    Args:
        device_id: Identifier of the device to update.
        payload: Device fields to update.
        project_db: Database session for the current project.
    """
    device = await project_db.get(core.models.Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail=DESCRIPTION_404)
    serial_number = payload.serial_number.strip() if payload.serial_number else None
    device.serial_number = serial_number or None
    await project_db.commit()
    await project_db.refresh(device)
    return interfaces.DeviceInterface(
        device_id=device.device_id,
        device_id_path=device.device_id_path,
        device_type_id=device.device_type_id,
        device_model_id=device.device_model_id,
        cec_pv_inverter_id=device.cec_pv_inverter_id,
        cec_pv_module_id=device.cec_pv_module_id,
        pv_module_id=device.pv_module_id,
        parent_device_id=device.parent_device_id,
        logical=device.logical,
        name_short=device.name_short,
        name_long=device.name_long,
        capacity_dc=device.capacity_dc,
        capacity_ac=device.capacity_ac,
        point=(
            interfaces.Point.model_validate(device.point)
            if device.point is not None
            else None
        ),
        polygon=(
            interfaces.MultiPolygon.model_validate(device.polygon)
            if device.polygon is not None
            else None
        ),
        serial_number=device.serial_number,
        device_type=None,
        name_full=None,
    )


@router.post(
    "",
    operation_id="get_project_devices_v2",
    summary="Get project devices with support for large filter lists",
    description="""
    V2 endpoint that solves the parameter limit issue when filtering by many
    device_type_ids.

    Supports multiple response formats:
    - json: Standard JSON response (default)
    - arrow: Apache Arrow IPC format for high-performance data transfer
    - parquet: Parquet format for efficient columnar storage

    Use POST method to send large filter lists in the request body instead of
    query parameters.

    Field filtering: Use the 'fields' parameter to return only specific fields,
    e.g., ["device_id", "name_long"].
    """,
)
async def get_project_devices_v2(
    *,
    filters: DevicesFilterRequest,
    project_db: Session = Depends(get_project_db),
):
    """Return filtered project devices supporting large payloads and formats.

    Args:
        filters: Request payload containing filtering, paging, and format options.
        project_db: Database session for the current project.
    """
    # Validate format
    if filters.format not in ["json", "arrow", "parquet"]:
        raise HTTPException(
            status_code=400, detail="Format must be one of: json, arrow, parquet"
        )

    # Handle large device_type_ids lists by chunking if necessary
    # SQLAlchemy typically has a limit around 32K-65K parameters

    project_schema = utils.get_project_schema(project_db=project_db)
    query_obj = core.crud.project.devices.get_project_devices(
        device_ids=filters.device_ids,
        device_type_ids=filters.device_type_ids,
        parent_device_ids=filters.parent_device_ids,
        name_short=filters.name_short,
        name_long=filters.name_long,
        deep=filters.deep,
        device_id_descendent_of=filters.device_id_descendent_of,
        with_tags=filters.with_tags,
        include_name_long=True,
    )

    devices_pd = await query_obj.get_async(
        output_type=OutputType.PANDAS,
        schema=project_schema,
    )
    devices_df = pl.from_pandas(devices_pd)

    # Define a helper function to safely convert WKB bytes to GeoJSON
    def wkb_to_geojson(wkb_bytes):  # no-star-syntax
        """Convert WKB bytes into a GeoJSON string representation.

        Args:
            wkb_bytes: Geometry data in Well-Known Binary format.
        """
        if wkb_bytes is None:
            return None

        # Handle empty bytes or invalid data
        if isinstance(wkb_bytes, bytes) and len(wkb_bytes) == 0:
            return None

        # Convert to bytes if it's not already
        if not isinstance(wkb_bytes, bytes):
            try:
                wkb_bytes = bytes(wkb_bytes)
            except (TypeError, ValueError):
                return None

        # Additional validation - WKB should have minimum length
        if len(wkb_bytes) < 4:  # WKB needs at least 4 bytes for header
            return None

        try:
            # loads() parses the raw WKB bytes into a Shapely geometry object
            # mapping() converts the Shapely object to a GeoJSON-like dictionary
            geom = wkb_loads(wkb_bytes)
            geojson = mapping(geom)
            return json.dumps(geojson)
        except Exception as e:
            # Log the specific error for debugging
            logger.warning(f"WKB parsing error: {e}, data length: {len(wkb_bytes)}")
            return None

    # Convert geometry fields using Polars native operations for better performance
    # Process point column if it exists
    if "point" in devices_df.columns:
        point_dtype = pl.Struct(
            [
                pl.Field("type", pl.Utf8),
                pl.Field("coordinates", pl.List(pl.Float64)),
            ]
        )
        devices_df = devices_df.with_columns(
            pl.col("point")
            .map_elements(wkb_to_geojson, return_dtype=pl.Utf8, skip_nulls=True)
            .str.json_decode(dtype=point_dtype)
            .alias("point")
        )

    # Process polygon column if it exists
    if "polygon" in devices_df.columns:
        # NOTE: The database guarantees that polygon data are valid
        # MULTIPOLYGONs (or nulls)
        multipolygon_dtype = pl.Struct(
            [
                pl.Field("type", pl.Utf8),
                pl.Field(
                    "coordinates",
                    pl.List(pl.List(pl.List(pl.List(pl.Float64)))),
                ),
            ]
        )
        devices_df = devices_df.map_columns(
            ["polygon"],
            lambda s: s.map_elements(
                wkb_to_geojson, return_dtype=pl.Utf8, skip_nulls=True
            ).str.json_decode(dtype=multipolygon_dtype),
        )
    # Add name_full column using Polars operations
    # Device Type Name Long is called name_long_1 because it is joined in
    # To Do:  Modify core to call it device type name long
    devices_df = devices_df.with_columns(
        (
            pl.col("name_long_1").fill_null("").str.replace_all("^$", "")
            + pl.lit(" ")
            + pl.col("name_long").fill_null("")
        ).alias("name_full")
    )

    # Apply natural sorting using natsorted for consistent behavior
    # We do this efficiently by extracting just the sorting column, sorting indices,
    # then reordering the DataFrame
    if len(devices_df) > 0:
        name_long_values = devices_df.select("name_long").to_series().to_list()
        sorted_indices = sorted(
            range(len(name_long_values)), key=lambda i: name_long_values[i] or ""
        )
        # Use natsorted to get the proper natural sort order
        sorted_name_values = natsorted(
            [(i, name_long_values[i] or "") for i in range(len(name_long_values))],
            key=lambda x: x[1],
        )
        sorted_indices = [x[0] for x in sorted_name_values]
        devices_df = devices_df[sorted_indices]

    # Apply pagination if requested
    if filters.limit is not None:
        devices_df = devices_df.slice(filters.offset, filters.limit)

    # Filter fields if specified
    if filters.fields:
        # Ensure we have all requested fields that exist in the DataFrame
        available_fields = [f for f in filters.fields if f in devices_df.columns]
        if available_fields:
            devices_df = devices_df.select(available_fields)

    # Return in requested format
    if filters.format == "json":
        return devices_df.to_dicts()

    elif filters.format == "arrow":
        return polars_to_arrow_response(df=devices_df, filename="devices.arrow")

    elif filters.format == "parquet":
        # Create Parquet buffer directly from Polars DataFrame
        buffer = io.BytesIO()
        devices_df.write_parquet(buffer)
        buffer.seek(0)

        return Response(
            content=buffer.getvalue(),
            media_type="application/parquet",
            headers={
                "Content-Disposition": "attachment; filename=devices.parquet",
                "X-Total-Records": str(len(devices_df)),
            },
        )
