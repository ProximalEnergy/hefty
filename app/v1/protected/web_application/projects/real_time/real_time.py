import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session

import core
from app import utils
from app._crud.projects.data_timeseries_latest import (
    get_data_timeseries_latest_by_device_type,
)
from app.dependencies import get_project_db

router = APIRouter(
    prefix="/real-time",
    tags=["real-time"],
    include_in_schema=utils.get_include_in_schema(),
)


# --- 1) helper to convert a DataTimeseriesLast row into a single float -------------
def _extract_numeric_value(*, row) -> float | None:
    """Return the first non-NULL numeric column from a DataTimeseriesLast row."""
    # todo: unit_offset is not applied in this function however it should probably be
    # applied in the get_data_timeseries_latest_by_device_type function instead
    for attr in (
        "value_integer",
        "value_bigint",
        "value_real",
        "value_double",
    ):
        value = getattr(row, attr)
        if value is not None:
            value = float(value)
            if row.tag.unit_scale is not None:
                value = value * row.tag.unit_scale
            return value
    return None


# --- 2) optional: human names for each sensor_type_id you care about --------------
SENSOR_TYPE_NAME = {
    2: "AC Power",
    3: "AC Power",
    9: "AC Power Setpoint",
    24: "Tracker Position",
    25: "Tracker Setpoint",
    27: "Combiner Current",
    31: "AC Power",
    45: "SOC",
    82: "Voltage",
    106: "AC Power",
    121: "AC Power",
}


# --- 3) the endpoint ----------------------------------------------------------------
@router.get("/{device_type_id}", response_class=ORJSONResponse)
def get_by_device_type_id(
    device_type_id: int,
    sensor_type_ids: Annotated[list[int] | None, Query()] = None,
    project_db: Session = Depends(get_project_db),
):
    # ── fetch latest values ─────────────────────────────────────────────────────
    data_rows = get_data_timeseries_latest_by_device_type(
        db=project_db,
        device_type_id=device_type_id,
        sensor_type_ids=sensor_type_ids,
        start=None,
    )

    if not data_rows:
        return {  # empty stub so TS side stays happy
            "device_ids": [],
            "device_names": [],
            "device_names_x": [],
            "device_names_y": [],
            "traces": [],
        }

    # ── build *unique* device list in deterministic order ───────────────────────
    device_ids: list[int] = []
    seen = set()
    for row in data_rows:
        did = row.tag.device_id
        if did not in seen:
            seen.add(did)
            device_ids.append(did)

    # ── device metadata (names) --------------------------------------------------
    devices = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_ids=device_ids,
        deep=False,
    ).models()
    devices = [d for d in devices if d.device_type_id != 0]
    device_ids = [d.device_id for d in devices]

    # id ➜ long_name lookup
    name_by_id = {d.device_id: d.name_long for d in devices}

    device_names: list[str | None] = [name_by_id[d] for d in device_ids]
    # device_names = natsorted(device_names)
    device_names_y: list[str] = [".".join(str(n).split(".")[:-1]) for n in device_names]
    device_names_x: list[str] = [str(n).split(".")[-1] for n in device_names]

    # ── organize the data into {sensor_type_id: {device_id: value}} -------------
    values_by_sensor: dict[int, dict[int, float | None]] = {}
    times_by_sensor: dict[int, dict[int, datetime.datetime]] = {}
    for row in data_rows:
        sid = row.tag.sensor_type_id
        did = row.tag.device_id
        values_by_sensor.setdefault(sid, {})[did] = _extract_numeric_value(row=row)
        times_by_sensor.setdefault(sid, {})[did] = row.time

    # ── convert to front-end "traces" shape -------------------------------------
    traces: list[dict[str, str | list]] = []
    for sensor_type_id, values_by_device in values_by_sensor.items():
        traces.append(
            {
                "name": SENSOR_TYPE_NAME.get(
                    sensor_type_id,
                    f"Sensor {sensor_type_id}",
                ),
                "values": [values_by_device.get(did) for did in device_ids],
                "times": [
                    times_by_sensor[sensor_type_id].get(did, None) for did in device_ids
                ],
            },
        )

    # ── final RealTimeData payload ---------------------------------------------
    return {
        "device_ids": device_ids,
        "device_names": device_names,
        "device_names_x": device_names_x,
        "device_names_y": device_names_y,
        "traces": traces,
    }
