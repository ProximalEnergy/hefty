import io
import json
from typing import Annotated

import polars as pl
import pyarrow as pa
from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from natsort import natsorted
from pydantic import BaseModel
from shapely.geometry import mapping
from shapely.wkb import loads as wkb_loads
from sqlalchemy.orm import Session

import core
from app import custom_types, interfaces, utils
from app.dependencies import get_project_db
from app.logger import logger

DESCRIPTION_404 = "Device not found"

router = APIRouter(prefix="/projects/{project_id}/devices", tags=["project_devices"])


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


@router.get(
    "/{device_id}",
    response_model=interfaces.Device,
    operation_id="get_project_device_by_id",
    responses={404: {"description": DESCRIPTION_404}},
)
async def get_project_device(
    device_id: int,
    deep: custom_types.AnnotatedDeep = False,
    project_db: Session = Depends(get_project_db),
):
    """Return a single project device with optional relationship data.

    Args:
        device_id: Identifier of the device to fetch.
        deep: Whether to include related entities such as children and tags.
        project_db: Database session for the current project.
    """
    schema_translate_map = (
        project_db.get_bind().get_execution_options().get("schema_translate_map", {})
    )
    project_schema = schema_translate_map.get("project")
    device = await core.crud.project.devices.get_project_device(
        device_id=device_id,
        deep=deep,
    ).get_async(output_type=OutputType.SQLALCHEMY, schema=project_schema)
    utils.check_404(value=device, detail=DESCRIPTION_404)
    return device


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

    # Get the query object and use polars_dataframe for v2
    query_obj = core.crud.project.devices.get_project_devices(
        project_db,
        device_ids=filters.device_ids,
        device_type_ids=filters.device_type_ids,
        parent_device_ids=filters.parent_device_ids,
        name_short=filters.name_short,
        name_long=filters.name_long,
        deep=filters.deep,
        device_id_descendent_of=filters.device_id_descendent_of,
        with_tags=filters.with_tags,
        include_name_long=True,
        return_query=True,
    )

    # Use polars_dataframe method for efficient data processing
    devices_df = await query_obj.polars_dataframe_async()

    # Define a helper function to safely convert WKB bytes to GeoJSON
    def wkb_to_geojson(wkb_bytes):  # nosemgrep: python-enforce-keyword-only-args
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
        # Create Arrow table directly from Polars DataFrame
        table = devices_df.to_arrow()

        # Create IPC buffer
        buffer = io.BytesIO()
        with pa.ipc.new_file(buffer, table.schema) as writer:
            writer.write_table(table)

        buffer.seek(0)

        return Response(
            content=buffer.getvalue(),
            media_type="application/vnd.apache.arrow.file",
            headers={
                "Content-Disposition": "attachment; filename=devices.arrow",
                "X-Total-Records": str(len(devices_df)),
            },
        )

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
