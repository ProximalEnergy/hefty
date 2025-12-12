import datetime
from typing import Annotated
from uuid import UUID

import numpy as np
import pandas as pd
from core.dependencies import get_db
from core.enumerations import DeviceType, KPIType, ProjectStatusType, SensorType
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

import core
from app import dependencies, interfaces, logger, utils
from app.v1.analytics import analytics_funcs as funcs
from app.v1.operational.kpi_data import get_kpi_data_helper
from core import models

router = APIRouter(prefix="/gis", include_in_schema=utils.get_include_in_schema())


@router.get("/pcs", response_class=ORJSONResponse)
def get_pcs(
    project_id: UUID,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    db: Session = Depends(get_db),
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project_api),
):
    devices_block = core.crud.project.devices.get_project_devices(
        project_db,
        device_type_ids=[DeviceType.BLOCK],
    ).models()

    devices_pcs = core.crud.project.devices.get_project_devices(
        project_db,
        device_type_ids=[DeviceType.PV_PCS],
    ).models()

    device_ids = [device.device_id for device in devices_pcs] + [
        device.device_id for device in devices_block
    ]

    block_device_id_to_pcs_device_ids = utils.map_ancestors_to_descendents(
        ancestors=devices_block,
        descendents=devices_pcs,
    )

    tags = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_name_shorts=["pv_pcs_ac_power"],
    ).models()

    tag_id_to_tag = {tag.tag_id: tag for tag in tags}

    live = start is None or end is None

    if live:
        end = pd.Timestamp.utcnow().floor("5min")
        start = end - pd.Timedelta(minutes=30)

        try:
            df_pcs = utils.data_df(
                project_db,
                project,
                tags,
                start=start,
                end=end,
                fillna_zero=False,
            ).astype(float)
            try:
                df_pcs_ep = (
                    funcs.get_expected_power(
                        project_id=project_id,
                        start=start,
                        end=end,
                        db=db,
                        project_db=project_db,
                        project=project,
                    )
                    / 1_000_000
                ).astype(float)
            except KeyError:
                df_pcs_ep = pd.DataFrame(index=df_pcs.index)
            missing_data = False
        except HTTPException:
            missing_data = True
            as_of = None

        if not missing_data:
            # Drop all rows that have all NaNs
            df_pcs = df_pcs.dropna(how="all")
            df_pcs_ep = df_pcs_ep.loc[df_pcs.index]

            if df_pcs.empty:
                missing_data = True
                as_of = None

            else:
                as_of = df_pcs.index[-1].isoformat()

                df_pcs.columns = pd.Index(
                    [
                        tag_id_to_tag[tag_id].device_id
                        for tag_id in df_pcs.columns.astype(int)
                    ],
                )

                df_block = pd.concat(
                    [
                        df_pcs[pcs_device_ids].sum(axis=1, min_count=1)
                        for pcs_device_ids in block_device_id_to_pcs_device_ids.values()
                    ],
                    axis=1,
                )
                df_block.columns = list(block_device_id_to_pcs_device_ids.keys())  # type: ignore

                df_block_ep = pd.concat(
                    [
                        df_pcs_ep[df_pcs_ep.columns.intersection(pcs_device_ids)].sum(
                            axis=1,
                            min_count=1,
                        )
                        for pcs_device_ids in block_device_id_to_pcs_device_ids.values()
                    ],
                    axis=1,
                )
                df_block_ep.columns = list(block_device_id_to_pcs_device_ids.keys())

                df = pd.concat([df_pcs, df_block], axis=1)
                df_ep = pd.concat([df_pcs_ep, df_block_ep], axis=1)

                power = (df.iloc[-1] * 1000).round(0).to_dict()
                power_exp = (df_ep.iloc[-1] * 1000).round(0).to_dict()
                power_norm_exp = (df / df_ep).clip(upper=1).round(3).iloc[-1].to_dict()

                # Identify any block ids that have a pcs device with offline inverter
                red_outline = {
                    block_device_id: any(
                        [
                            power[pcs_device_id] == 0
                            for pcs_device_id in block_device_id_to_pcs_device_ids[
                                block_device_id  # type: ignore
                            ]
                        ],
                    )
                    for block_device_id in df_block
                }

        data = {
            "as_of": as_of,
            "data": {
                device_id: {
                    "power": power[device_id] if not missing_data else np.nan,
                    "power_exp": power_exp.get(device_id, np.nan)
                    if not missing_data
                    else np.nan,
                    "power_norm_exp": (
                        power_norm_exp.get(device_id, np.nan)
                        if not missing_data
                        else np.nan
                    ),
                    "energy": np.nan,
                    "red_outline": (
                        red_outline.get(device_id, False) if not missing_data else False
                    ),
                }
                for device_id in device_ids
            },
        }

    else:
        try:
            # df_pcs = get_project_pcs_energy_production(
            #     project_id, start, end, db, project_db
            # )
            if start and end:
                kpi_data = get_kpi_data_helper(
                    db=db,
                    start=start.date(),
                    end=end.date(),
                    project_ids=[project_id],
                    kpi_type_ids=[KPIType.PV_PCS_ENERGY_PRODUCTION],
                    include_device_data=True,
                )
                df_pcs = pd.DataFrame(
                    kpi_data[0]["data"]["device_data_obj"]["device_values"],
                    index=kpi_data[0]["data"]["dates"],
                )
                missing_data = False
            else:
                missing_data = True
        except HTTPException:
            missing_data = True

        if not missing_data:
            df_pcs.columns = [int(col) for col in df_pcs.columns]  # type: ignore

            df_block = pd.concat(
                [
                    df_pcs[pcs_device_ids].sum(axis=1, min_count=1)
                    for pcs_device_ids in block_device_id_to_pcs_device_ids.values()
                ],
                axis=1,
            )
            df_block.columns = list(block_device_id_to_pcs_device_ids.keys())  # type: ignore

            df = pd.concat([df_pcs, df_block], axis=1)

            energy = df.sum().astype(int).to_dict()

        data = {
            "as_of": None,
            "data": {
                device_id: {
                    "power": np.nan,
                    "power_exp": np.nan,
                    "power_norm_exp": np.nan,
                    "energy": energy[device_id] if not missing_data else np.nan,
                    "red_outline": False,
                }
                for device_id in device_ids
            },
        }

    return data


@router.get("/tracker", response_model=interfaces.GeoJSON)
def get_tracker(
    start: datetime.date,
    end: datetime.date,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    # Get PV Block devices
    devices = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_type_ids=[DeviceType.BLOCK],
    ).models()

    # Get KPI data
    kpi_data_dict = utils.kpi_data_list_to_dict(
        kpi_data=get_kpi_data_helper(
            db=project_db,
            start=start,
            end=end,
            kpi_type_ids=[
                KPIType.TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_BLOCK,
                KPIType.TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_BLOCK,
            ],
            project_ids=[project.project_id],
            include_device_data=True,
        ),
        key="kpi_type_id",
    )

    # Look for KPI data by KPI type id
    kpi_data_pos_block = kpi_data_dict.get(18)
    kpi_data_sp_block = kpi_data_dict.get(19)

    # If KPI data is not found, use empty Series
    if kpi_data_pos_block is None or kpi_data_sp_block is None:
        s_pos_block, s_sp_block = pd.Series(), pd.Series()

    # If KPI data is found, parse the data and take the mean
    else:
        s_pos_block = (
            utils.parse_kpi_data_to_df(kpi_data=kpi_data_pos_block).mean().round(2)
        )
        s_sp_block = (
            utils.parse_kpi_data_to_df(kpi_data=kpi_data_sp_block).mean().round(2)
        )

    # Create GeoJSON data
    return_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": device.name_long,
                    "device_id": device.device_id,
                    "position_deviation": s_pos_block.get(device.device_id),
                    "setpoint_deviation": s_sp_block.get(device.device_id),
                },
                "geometry": device.polygon,
            }
            for device in devices
        ],
    }

    return return_data


@router.get("/tracker-by-block/{block_id}", response_model=interfaces.GeoJSON)
def get_tracker_by_block(
    block_id: int,
    start: datetime.date,
    end: datetime.date,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    # Get tracker rows which are descendents of the block
    devices = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_type_ids=[DeviceType.TRACKER_ROW],
        device_id_descendent_of=block_id,
    ).models()

    # Get KPI data
    kpi_data_dict = utils.kpi_data_list_to_dict(
        kpi_data=get_kpi_data_helper(
            db=project_db,
            start=start,
            end=end,
            kpi_type_ids=[
                KPIType.TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_ROW,
                KPIType.TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_ROW,
            ],
            project_ids=[project.project_id],
            include_device_data=True,
        ),
        key="kpi_type_id",
    )

    # Look for KPI data by KPI type id
    kpi_data_pos_row = kpi_data_dict.get(21)
    kpi_data_sp_row = kpi_data_dict.get(22)

    # If KPI data is not found, use empty Series
    if kpi_data_pos_row is None or kpi_data_sp_row is None:
        s_pos_row, s_sp_row = pd.Series(), pd.Series()

    # If KPI data is found, parse the data and take the mean
    else:
        s_pos_row = (
            utils.parse_kpi_data_to_df(kpi_data=kpi_data_pos_row)
            .apply(pd.to_numeric, errors="coerce")
            .mean()
            .astype(float)
            .round(2)
        )
        s_sp_row = (
            utils.parse_kpi_data_to_df(kpi_data=kpi_data_sp_row)
            .apply(pd.to_numeric, errors="coerce")
            .mean()
            .astype(float)
            .round(2)
        )

    # Create GeoJSON data
    return_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": device.name_long,
                    "position_deviation": s_pos_row.get(device.device_id),
                    "setpoint_deviation": s_sp_row.get(device.device_id),
                },
                "geometry": device.polygon,
            }
            for device in devices
        ],
    }

    return return_data


@router.get("/bess-enclosure", response_model=interfaces.GeoJSON)
def get_bess_enclosure(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    # BESS Enclosure devices
    devices = core.crud.project.devices.get_project_devices(
        project_db, device_type_ids=[DeviceType.BESS_ENCLOSURE]
    ).models()

    features = [
        {
            "type": "Feature",
            "properties": {
                "name_long": device.name_long,
            },
            "geometry": device.polygon,
        }
        for device in devices
    ]

    return_data = {
        "type": "FeatureCollection",
        "features": features,
    }

    return return_data


@router.get("/devices-in-viewport", response_class=ORJSONResponse)
def get_devices_in_viewport(
    north: float,
    east: float,
    south: float,
    west: float,
    device_type_ids: Annotated[list[int] | None, Query()] = None,
    power_device_type_id: Annotated[int | None, Query()] = None,
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project_api),
):
    """
    Retrieves devices whose geometry intersects the viewport bounding box (with buffer).
    Optionally filters by device_type_ids.
    If power_device_type_id is provided, fetches and includes latest actual/expected power
    for devices matching that type within the viewport.
    """
    # Base query for devices using ORM
    query = project_db.query(models.Device)

    # Optional filter by general device type IDs
    if device_type_ids:
        query = query.filter(models.Device.device_type_id.in_(device_type_ids))

    # Use the buffer calculation from the provided example
    width = east - west
    height = north - south
    buffer_size = max(width * 2, height * 2)

    # Define the spatial filter using a single text() clause, mirroring the example
    spatial_filter_sql = text(
        """
        (
            (polygon IS NOT NULL AND ST_Intersects(polygon, ST_Buffer(ST_MakeEnvelope(:west, :south, :east, :north, 4326), :buffer_size)))
            OR
            (point IS NOT NULL AND ST_Intersects(point, ST_Buffer(ST_MakeEnvelope(:west, :south, :east, :north, 4326), :buffer_size)))
        )
        """,
    ).bindparams(
        west=west,
        south=south,
        east=east,
        north=north,
        buffer_size=buffer_size,
    )

    # Apply the spatial filter
    query = query.filter(spatial_filter_sql)

    # Execute the query
    devices = query.all()

    # --- Optional Additional Data Fetching (Power or Tracker Angle) ---
    # This will hold data like: {device_id: {"actual": ..., "expected_soiled": ...}} or
    # {device_id: {"tracker_angle": ...}}
    all_device_extra_data = {}

    # 1. Fetch data for the primary power_device_type_id
    if power_device_type_id is not None:
        primary_data_device_ids = [
            dev.device_id
            for dev in devices
            if dev.device_type_id == power_device_type_id
        ]
        if primary_data_device_ids:
            try:
                primary_extra_data = utility_expected(
                    device_ids=primary_data_device_ids,
                    project_db=project_db,
                    project=project,
                )
                all_device_extra_data.update(primary_extra_data)
            except Exception as e:  # Catch a broader range of exceptions
                logger.logger.error(
                    f"Error fetching primary additional data for type {power_device_type_id}: {e}"
                )

    # 2. Fetch power data for any PCS (type 2) devices if not already fetched as primary
    if (
        power_device_type_id != DeviceType.PV_PCS
    ):  # Check if PCS wasn't the primary type
        # Identify PCS devices that are in the viewport AND don't already have their data fetched
        pcs_to_fetch_ids = [
            dev.device_id
            for dev in devices
            if dev.device_type_id == DeviceType.PV_PCS
            and dev.device_id not in all_device_extra_data
        ]
        if pcs_to_fetch_ids:
            logger.logger.info(
                f"Fetching supplementary power data for PCS devices: {pcs_to_fetch_ids}"
            )
            try:
                pcs_extra_data = utility_expected(
                    device_ids=list(set(pcs_to_fetch_ids)),  # Ensure unique IDs
                    project_db=project_db,
                    project=project,
                )
                all_device_extra_data.update(pcs_extra_data)
            except Exception as e:  # Catch a broader range of exceptions
                logger.logger.error(f"Error fetching supplementary PCS power data: {e}")

    # 3. Fetch latest data for any Met Station (type 4) devices
    met_station_to_fetch_ids = [
        dev.device_id
        for dev in devices
        if dev.device_type_id == DeviceType.MET_STATION
        and dev.device_id not in all_device_extra_data
    ]
    if met_station_to_fetch_ids:
        try:
            met_station_data_values = get_met_station_latest_values(
                device_ids=list(set(met_station_to_fetch_ids)),  # Ensure unique IDs
                project_db=project_db,
                project=project,
            )
            # The met_station_data_values is already in the format {device_id: {poa: val, ghi: val, ...}}
            # We need to merge this carefully if a device_id could somehow already be in all_device_extra_data
            # with a different structure, though for Met Stations this step is distinct.
            for dev_id, data_vals in met_station_data_values.items():
                if dev_id not in all_device_extra_data:  # Should typically be true
                    all_device_extra_data[dev_id] = data_vals
                else:  # If it exists, assume it's from a previous step and merge if necessary (unlikely for met stations)
                    if isinstance(all_device_extra_data[dev_id], dict) and isinstance(
                        data_vals, dict
                    ):
                        all_device_extra_data[dev_id].update(data_vals)
                    else:
                        all_device_extra_data[dev_id] = (
                            data_vals  # Overwrite if types are incompatible for merge
                        )
        except HTTPException as e:
            # Catch HTTP exceptions (like 404 Not Found) specifically.
            # Log as info or warning, not error, as this can be an expected state.
            if e.status_code == 404:
                logger.logger.info(
                    f"Met Station data not found (as expected): {e.detail}"
                )
            else:
                logger.logger.warning(f"HTTP error fetching Met Station data: {e}")
        except Exception as e:
            # Catch any other unexpected errors.
            logger.logger.error(
                f"An unexpected error occurred fetching Met Station data: {e}"
            )

    # --- Prepare Response ---
    # Convert devices to dicts and merge additional data if available
    response_data = []
    for device in devices:
        # Use Pydantic model for serialization using modern methods
        device_schema = interfaces.Device.model_validate(device)
        device_dict = device_schema.model_dump()

        # Get the specific extra data for this device, if any
        extra_data_for_this_device = all_device_extra_data.get(device.device_id)

        if extra_data_for_this_device:
            if device.device_type_id == DeviceType.TRACKER_ROW:
                device_dict["tracker_data"] = extra_data_for_this_device
            # Assuming PCS (2, 13) and Combiner (9) expect their data under "power_data"
            # and utility_expected returns the payload directly for these types.
            elif device.device_type_id in [
                DeviceType.PV_PCS,
                DeviceType.PV_DC_COMBINER,
                DeviceType.BESS_PCS,
            ]:
                device_dict["power_data"] = extra_data_for_this_device
            elif device.device_type_id == DeviceType.MET_STATION:
                # extra_data_for_this_device should be the dict like {poa: val, ...}
                device_dict["met_station_values"] = extra_data_for_this_device
            # Add other device type specific data handling here if utility_expected supports them
        else:
            # Ensure keys for power_data or tracker_data are present (as None) for frontend consistency if expected
            if device.device_type_id == DeviceType.TRACKER_ROW:
                device_dict["tracker_data"] = None
            elif device.device_type_id in [
                DeviceType.PV_PCS,
                DeviceType.PV_DC_COMBINER,
                DeviceType.BESS_PCS,
            ]:
                device_dict["power_data"] = None
            elif device.device_type_id == DeviceType.MET_STATION:
                device_dict["met_station_values"] = None
            # Met stations (type 4) etc. won't have these keys added here unless explicitly handled

        response_data.append(device_dict)

    return ORJSONResponse(content=response_data)


# Removed @router.post decorator - this is now an internal helper function
def utility_expected(
    *,
    device_ids: list[int],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project_api),
):
    """
    This function facilitates backend data required for GIS viewport.
    If device type is Tracker Row (29), fetches latest tracker angle.
    Otherwise, fetches actual/expected power for supported power device types.
    Accepts one or more device IDs (must be of the same supported type).
    If start/end are None for power types, fetches data for the latest hour.
    """
    # Handle optional start/end dates (only relevant for power types now)
    if start is None or end is None:
        end = pd.Timestamp.utcnow().floor("5min")
        start = end - pd.Timedelta(hours=1)

    if not device_ids:
        raise HTTPException(status_code=400, detail="No device IDs provided")

    # --- Device Type Validation ---
    # Fetch devices once for validation and later use
    devices = core.crud.project.devices.get_project_devices(
        project_db, device_ids=device_ids
    ).models()
    if len(devices) != len(device_ids):
        missing_ids = set(device_ids) - set(d.device_id for d in devices)
        raise HTTPException(
            status_code=404,
            detail=f"Device IDs not found: {missing_ids}",
        )

    # Store devices in a dict for easier access later
    device_dict = {dev.device_id: dev for dev in devices}

    first_device_type_id = devices[0].device_type_id
    if not all(d.device_type_id == first_device_type_id for d in devices):
        raise HTTPException(
            status_code=422,
            detail="All device IDs must be of the same type.",
        )
    # --- Handle Tracker Row Case ---
    if first_device_type_id == DeviceType.TRACKER_ROW:
        sensor_type_ids = [SensorType.TRACKER_POSITION]
        tags = core.crud.project.tags.get_project_tags(
            project_db,
            device_ids=device_ids,
            sensor_type_ids=sensor_type_ids,
        ).models()
        if not tags:
            # Return empty dict if no tags found, endpoint will handle merging None
            return {}

        # Fetch latest data point using data_latest_df
        try:
            df_latest = utils.data_df(
                project_db,
                project,
                tags=tags,
                start=start - pd.Timedelta(hours=3),
                end=end,
            )
        except HTTPException:
            # Handle cases where data_latest_df might fail (e.g., no data at all)
            return {}

        if df_latest.empty:
            return {}

        # Structure the result
        results = {}
        tag_id_to_device_id = {tag.tag_id: tag.device_id for tag in tags}
        # data_latest_df returns a Series with tag_id as index
        latest_values = df_latest.iloc[-1]  # Get the row of latest values

        for tag_id, value in latest_values.items():
            dev_id = tag_id_to_device_id.get(int(tag_id))  # type: ignore
            if dev_id is not None:
                results[dev_id] = {
                    "tracker_angle": value if pd.notna(value) else None,
                    # Add timestamp if needed, available from df_latest.index[0]
                    # "timestamp": df_latest.index[0].isoformat()
                }

        return results

    # --- Existing Power Logic (for non-tracker types) ---

    # --- Determine Parameters based on Device Type ---
    pv_dc_combiner_case = False
    sensor_type_ids = []  # Initialize for non-combiner case
    if first_device_type_id == DeviceType.PV_PCS:
        sensor_type_ids = [SensorType.PV_PCS_AC_POWER]
        # Add fallback expected metric IDs for PCS (expected_metric_type_id 2)
        # Try with soiling first (10), then without soiling (9), then with degradation (3), then without degradation (4)
        expected_metric_ids_fallback = [10, 9, 4, 3]
        multiplier = 1_000.0  # Raw data presumed in kW?
        expected_device_ids_for_query = device_ids
    elif first_device_type_id == DeviceType.PV_DC_COMBINER:
        # Add fallback expected metric IDs for Combiner (expected_metric_type_id 1)
        # Try with soiling first (8), then without soiling (7), then with degradation (1), then without degradation (2)
        expected_metric_ids_fallback = [8, 7, 2, 1]
        multiplier = 1 / 1_000  # V * A = W -> kW
        expected_device_ids_for_query = device_ids
        pv_dc_combiner_case = True
    elif first_device_type_id == DeviceType.BESS_PCS.value:  # BESS PCS
        sensor_type_ids = [SensorType.BESS_PCS_AC_POWER]  # BESS PCS AC Power
        # BESS devices don't have expected power data like PV devices
        expected_metric_ids_fallback = []
        multiplier = 1_000.0  # Raw data presumed in kW?
        expected_device_ids_for_query = device_ids
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported device type ID: {first_device_type_id}",
        )

    # --- Query and Calculate Actual Device Data ---
    df_actual = pd.DataFrame()  # Initialize

    if pv_dc_combiner_case:
        # --- Combiner Specific Actual Power Calculation (Optimized) ---

        # 1. Find parent PCS IDs from input combiners
        # Combiners can be children of either PCSs (type 2) or PCS Modules (type 3)
        # If parent is a module, we need to get the module's parent (the PCS)
        parent_ids_with_none = {
            device_dict[dev_id].parent_device_id
            for dev_id in device_ids
            if device_dict[dev_id].parent_device_id is not None
        }

        if not parent_ids_with_none:
            raise HTTPException(
                status_code=404,
                detail="Could not determine parent device IDs for the given combiners.",
            )

        # Fetch parent devices to check their types
        parent_device_ids = [pid for pid in parent_ids_with_none if pid is not None]
        parent_devices = core.crud.project.devices.get_project_devices(
            project_db,
            device_ids=parent_device_ids,
        ).models()
        parent_device_dict = {dev.device_id: dev for dev in parent_devices}

        # Determine PCS IDs: if parent is a module (type 3), get its parent; if it's a PCS (type 2), use it directly
        parent_pcs_ids = []
        combiner_to_parent_pcs_id = {}
        for dev_id in device_ids:
            parent_id = device_dict[dev_id].parent_device_id
            if parent_id is None:
                continue

            parent_device = parent_device_dict.get(parent_id)
            if parent_device is None:
                continue

            # If parent is a PCS Module (type 3), get its parent (the PCS)
            if parent_device.device_type_id == DeviceType.PV_PCS_MODULE:
                pcs_id = parent_device.parent_device_id
                if pcs_id is not None:
                    parent_pcs_ids.append(pcs_id)
                    combiner_to_parent_pcs_id[dev_id] = pcs_id
            # If parent is already a PCS (type 2), use it directly
            elif parent_device.device_type_id == DeviceType.PV_PCS:
                parent_pcs_ids.append(parent_id)
                combiner_to_parent_pcs_id[dev_id] = parent_id
            else:
                # Unexpected parent type
                raise HTTPException(
                    status_code=422,
                    detail=f"Combiner {dev_id} has unexpected parent device type {parent_device.device_type_id}.",
                )

        # Remove duplicates from parent_pcs_ids
        parent_pcs_ids = list(set(parent_pcs_ids))

        if not parent_pcs_ids:
            raise HTTPException(
                status_code=404,
                detail="Could not determine parent PCS IDs for the given combiners.",
            )

        # DB Call 1: Fetch all relevant PV PCS Modules using parent IDs
        all_pcs_modules = core.crud.project.devices.get_project_devices(
            project_db,
            device_type_ids=[DeviceType.PV_PCS_MODULE],
            parent_device_ids=parent_pcs_ids,  # type: ignore # Use direct parent IDs
        ).models()
        module_ids = [mod.device_id for mod in all_pcs_modules]

        # Build mapping from parent PCS ID to its module IDs
        parent_pcs_id_to_module_ids: dict[int, list[int]] = {}
        for mod in all_pcs_modules:
            pcs_id = mod.parent_device_id
            if pcs_id is not None:  # Ensure parent_device_id is not None
                if pcs_id not in parent_pcs_id_to_module_ids:
                    parent_pcs_id_to_module_ids[pcs_id] = []
                parent_pcs_id_to_module_ids[pcs_id].append(mod.device_id)

        if not module_ids:
            # Consider if this check is still needed if parent_pcs_id_to_module_ids handles empty cases
            raise HTTPException(
                status_code=404,
                detail="Could not find PV PCS Modules for parent PCS devices.",
            )

        # DB Call for current tags (combiners)
        tags_current = core.crud.project.tags.get_project_tags(
            project_db,
            device_ids=device_ids,
            sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT],
        ).models()

        if not tags_current:
            return {}

        # DB Call for voltage tags (primary: module-level, fallback: PCS-level)
        using_pcs_level_voltage = False
        tags_voltage = core.crud.project.tags.get_project_tags(
            project_db,
            device_ids=module_ids,
            sensor_type_ids=[SensorType.PV_PCS_MODULE_DC_VOLTAGE],
        ).models()

        if not tags_voltage:
            tags_voltage = core.crud.project.tags.get_project_tags(
                project_db,
                device_ids=parent_pcs_ids,  # Use PCS device IDs for fallback
                sensor_type_ids=[SensorType.PV_PCS_DC_VOLTAGE],
            ).models()
            using_pcs_level_voltage = True

        if not tags_voltage:
            return {}

        # Create maps directly from the specific tag lists
        voltage_tag_map = {tag.device_id: tag.tag_id for tag in tags_voltage}
        current_tag_map = {tag.device_id: tag.tag_id for tag in tags_current}

        # Combine tag IDs for the data query
        list(voltage_tag_map.values()) + list(
            current_tag_map.values(),
        )

        # DB Call 4: Fetch all timeseries data
        df_data_raw = utils.data_df(
            project_db,
            project,
            tags=tags_voltage + tags_current,
            start=start,
            end=end,
        )  # Pass combined list of Tag objects

        if df_data_raw.empty:
            return {}

        # Map columns to device IDs for calculation
        # Use the maps created above
        tag_id_to_device_id_map = {v: k for k, v in voltage_tag_map.items()}
        tag_id_to_device_id_map.update({v: k for k, v in current_tag_map.items()})
        df_data = df_data_raw.rename(columns=tag_id_to_device_id_map)

        # Calculate power for each combiner
        actual_power_series_list = []
        for dev_id in device_ids:  # Use filtered list of combiners
            parent_pcs_id = combiner_to_parent_pcs_id.get(dev_id)
            if not parent_pcs_id:
                continue

            if using_pcs_level_voltage:
                # Fallback: Use the single voltage value from the parent PCS directly
                s_voltage = df_data.get(parent_pcs_id)
            else:
                # Primary: Calculate mean voltage from module-level data
                related_module_ids_for_parent = parent_pcs_id_to_module_ids.get(
                    parent_pcs_id, []
                )
                voltage_cols_present = [
                    m_id
                    for m_id in related_module_ids_for_parent
                    if m_id in df_data.columns
                ]
                if not voltage_cols_present:
                    continue
                s_voltage = df_data[voltage_cols_present].mean(axis=1)

            current_col = dev_id
            if (
                current_col not in df_data.columns
                or s_voltage is None
                or s_voltage.empty
            ):
                continue

            s_current = df_data[current_col]
            s_power_kw = s_voltage.mul(s_current) * multiplier
            s_power_kw.name = dev_id
            actual_power_series_list.append(s_power_kw)

        if not actual_power_series_list:
            return {}

        df_actual = pd.concat(actual_power_series_list, axis=1)

    else:
        # --- Standard Actual Power Fetching (Meter, PCS) ---
        tags = core.crud.project.tags.get_project_tags(
            project_db,
            device_ids=device_ids,
            sensor_type_ids=sensor_type_ids,
        ).models()
        if not tags:
            if project.project_status_type_id == ProjectStatusType.ONBOARDING.value:
                logger.logger.warning(
                    f"No suitable power tags found for device IDs {device_ids} "
                    f"with sensor types {sensor_type_ids}. "
                    f"This is normal during project onboarding "
                    "when tags are not yet configured."
                )
                return {}
            else:
                raise HTTPException(
                    status_code=404,
                    detail="No suitable power tags found for device IDs "
                    f"{device_ids} with sensor types {sensor_type_ids}.",
                )

        tag_id_to_device_id = {tag.tag_id: tag.device_id for tag in tags}

        df_actual_raw = utils.data_df(
            project_db,
            project,
            tags=tags,
            start=start,
            end=end,
        )

        if df_actual_raw.empty:
            # Return empty result or raise error? Returning empty for now.
            return {}

        # Map columns to device_id and apply multiplier
        df_actual_raw.columns = df_actual_raw.columns.map(tag_id_to_device_id)
        df_actual = df_actual_raw * multiplier

        # Ensure timezone conversion happens correctly
        df_actual.index = pd.to_datetime(df_actual.index).tz_convert(project.time_zone)

    # --- Query Expected Data with Fallbacks ---
    data_expected = None
    found_metric_id = None
    for expected_metric_id in expected_metric_ids_fallback:
        data_expected = core.crud.project.data_expected.get_project_data_expected(
            project_db,
            start=start,
            end=end,
            device_ids=expected_device_ids_for_query,
            expected_metric_ids=[expected_metric_id],
        ).models()
        if len(data_expected) > 0:
            found_metric_id = expected_metric_id
            break  # Found data, stop trying fallbacks

    if not data_expected or len(data_expected) == 0:
        # If no expected data, we might still return actual, or raise/return empty
        # Let's return actual data only in this case.
        df_expected_pivot = pd.DataFrame(index=df_actual.index)  # Empty DF
        df_expected_all = pd.DataFrame()  # Empty DF
    else:
        df_expected_all = pd.DataFrame([d.__dict__ for d in data_expected])
        # Pivot to get time index and device_id columns
        try:
            # Filter for the required metric ID *before* pivoting
            df_expected_filtered = df_expected_all[
                df_expected_all["expected_metric_id"] == found_metric_id
            ]

            if df_expected_filtered.empty:
                # Handle case where the specific metric ID isn't found
                df_expected_pivot = pd.DataFrame(index=df_actual.index)  # Empty DF
                df_expected_all = (
                    pd.DataFrame()
                )  # Ensure this is also empty for later logic
            else:
                # Pivot the *filtered* DataFrame
                df_expected_pivot = df_expected_filtered.pivot(
                    index="time",
                    columns="device_id",
                    values="value",
                )
                # Reindex expected to match actual timestamps and handle timezone
                df_expected_pivot = df_expected_pivot.reindex(
                    df_actual.index,
                    method="nearest",
                    limit=1,
                )  # Use nearest neighbor fill
                df_expected_pivot.index = pd.to_datetime(
                    df_expected_pivot.index,
                ).tz_convert(project.time_zone)
                df_expected_pivot = df_expected_pivot / 1_000  # Convert from W to kW
        except Exception as e:
            # Handle potential pivot errors (e.g., duplicate index/column entries)
            # Log the error? For now, create empty DF
            logger.logger.error(f"Error pivoting expected data: {e}")  # Basic logging
            df_expected_pivot = pd.DataFrame(index=df_actual.index)
            df_expected_all = pd.DataFrame()  # Ensure it's empty if pivot fails

    # --- Structure Output ---
    results = {}
    # Convert index to ISO format strings for JSON serialization
    times_list_iso = [ts.isoformat() for ts in df_actual.index]

    # Determine which expected column to use based on device type
    expected_col_key = expected_device_ids_for_query[
        0
    ]  # e.g., 1 for Meter, or first PCS id

    for dev_id in device_ids:
        actual_power_series = df_actual.get(
            dev_id,
            pd.Series(index=df_actual.index, dtype=float),
        )  # Handle missing actual data column

        # Get expected data (use the determined column key)
        expected_power_series = df_expected_pivot.get(
            dev_id,
            pd.Series(index=df_actual.index, dtype=float),
        )

        # Get unique versions for the expected device id column
        unique_versions = []
        if (
            not df_expected_all.empty
            and "device_id" in df_expected_all.columns
            and expected_col_key in df_expected_all["device_id"].values
        ):
            unique_versions = sorted(
                df_expected_all[df_expected_all["device_id"] == expected_col_key][
                    "version"
                ]
                .dropna()
                .unique()
                .tolist(),
            )

        results[dev_id] = {
            "times": times_list_iso,
            "actual": {
                "power": actual_power_series.where(
                    pd.notna(actual_power_series),
                    None,
                ).tolist(),
            },  # Convert NaN to None for JSON
            "expected_soiled": {
                "power": expected_power_series.where(
                    pd.notna(expected_power_series),
                    None,
                ).tolist(),
                "unique_versions": unique_versions,
            },
        }

    return results


def get_met_station_latest_values(
    *,
    device_ids: list[int],
    project_db: Session,
    project: models.Project,
) -> dict:
    """
    Fetches the latest sensor values (POA, GHI, Ambient Temp, Wind Speed)
    for the given Met Station device IDs.
    """
    if not device_ids:
        return {}

    met_sensor_type_names = [
        "met_station_poa",
        "met_station_ghi",
        "met_station_ambient_temperature",
        "met_station_wind_speed",
    ]

    try:
        # Assuming core.crud.project.tags.get_project_tags is synchronous
        tags = core.crud.project.tags.get_project_tags(
            project_db,
            device_ids=device_ids,
            sensor_type_name_shorts=met_sensor_type_names,  # Use names to find IDs
        ).models()
        if not tags:
            logger.logger.info(
                f"No relevant Met Station tags found for devices: {device_ids}"
            )
            return {}

        # --- Manually load the sensor_type relationship ---
        sensor_type_ids = list(
            set(tag.sensor_type_id for tag in tags if tag.sensor_type_id)
        )

        if sensor_type_ids:
            sensor_types = (
                project_db.query(models.SensorType)
                .filter(models.SensorType.sensor_type_id.in_(sensor_type_ids))
                .all()
            )
            logger.logger.info(f"Loaded {len(sensor_types)} sensor types")
            sensor_type_map = {st.sensor_type_id: st for st in sensor_types}
            # Associate the loaded SensorType objects back to the Tag objects
            for tag in tags:
                tag.sensor_type = (
                    sensor_type_map.get(tag.sensor_type_id)
                    if tag.sensor_type_id
                    else None
                )

        end_time = pd.Timestamp.utcnow().floor("5min")
        start_time = end_time - pd.Timedelta(hours=3)

        # Use data_df with time window
        df_met_data_raw = utils.data_df(
            project_db,
            project,
            tags=tags,
            start=start_time,
            end=end_time,
        )

        if df_met_data_raw.empty:
            logger.logger.info(
                f"No recent Met Station data found for devices: {device_ids}"
            )
            return {}

        latest_values: dict[int, dict[str, float]] = {}
        tag_map = {tag.tag_id: tag for tag in tags}

        for tag_id_str in df_met_data_raw.columns:
            tag_id = int(tag_id_str)
            series = df_met_data_raw[tag_id_str].dropna()
            if not series.empty:
                tag_info = tag_map.get(tag_id)
                if not tag_info:
                    logger.logger.warning(
                        f"Tag ID {tag_id} from data_df not found in tag_map. Skipping."
                    )
                    continue

                device_id = tag_info.device_id
                sensor_short_name = (
                    tag_info.sensor_type.name_short if tag_info.sensor_type else None
                )
                value = float(series.iloc[-1])  # Convert numpy float to Python float

                if device_id not in latest_values:
                    latest_values[device_id] = {}

                if sensor_short_name == "met_station_poa":
                    latest_values[device_id]["poa"] = value
                elif sensor_short_name == "met_station_ghi":
                    latest_values[device_id]["ghi"] = value
                elif sensor_short_name == "met_station_ambient_temperature":
                    latest_values[device_id]["ambient_temp"] = value
                elif sensor_short_name == "met_station_wind_speed":
                    latest_values[device_id]["wind_speed"] = value

        return latest_values  # Return the dictionary directly, FastAPI will handle JSON serialization

    except HTTPException as e:
        if e.status_code == 404:
            logger.logger.info(
                f"No data found for Met Station devices {device_ids}: {e.detail}"
            )
        else:
            logger.logger.error(
                f"HTTP error while fetching Met Station data for devices {device_ids}: {e}"
            )
        return {}
    except Exception as e:
        logger.logger.error(
            f"An unexpected error occurred while fetching Met Station data for devices {device_ids}: {e}"
        )
        return {}
