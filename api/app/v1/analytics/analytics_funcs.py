import datetime
from uuid import UUID

import numpy as np
import pandas as pd
import pvlib
from app.v1.analytics import analytics_vars as vars
from app.v1.operational.project.project_data import get_project_dataframe
from core.enumerations import SensorType
from sqlalchemy.orm import Session

import core
from core import models


def get_expected_power(
    *,
    project_id: UUID,
    start: datetime.datetime | None,
    end: datetime.datetime | None,
    db: Session,
    project_db: Session,
    project: models.Project,
):
    """todo

    Args:
        project_id: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
    """
    project_name_short = project.name_short

    module = vars.MODULE_DATA[vars.PROJECT_DEVICE_MAP[project_name_short]["module"]]
    inverter = vars.INVERTER_DATA[
        vars.PROJECT_DEVICE_MAP[project_name_short]["inverter"]
    ]
    location = vars.PROJECT_LOCATION_MAP[project_name_short]
    params = vars.PROJECT_PARAMS[project_name_short]

    df_met = get_project_dataframe(
        tag_ids=[],
        sensor_type_ids=[
            SensorType.MET_STATION_POA,
            SensorType.MET_STATION_AMBIENT_TEMPERATURE,
            SensorType.MET_STATION_WIND_SPEED,
        ],
        sensor_type_name_shorts=[],
        start=start,
        end=end,
        db=db,
        project_db=project_db,
        project=project,
    )

    df_met.index = pd.to_datetime(df_met.index)
    df_met = df_met.astype(float)

    # POA
    df_poa = df_met.xs("met_station_poa", level="sensor_type_name_short", axis=1)
    df_poa = df_poa[df_poa > 0]  # Remove negative values
    s_poa = df_poa.mean(axis=1).fillna(0)
    s_poa.name = "poa"

    df_t = df_met.xs(
        "met_station_ambient_temperature",
        level="sensor_type_name_short",
        axis=1,
    )

    if project_name_short == "assembly_1":
        s_t = df_t.mean(axis=1).fillna(0)
    elif project_name_short == "assembly_2":
        s_t = df_t[[43, 44, 45]].mean(axis=1).fillna(0)
    elif project_name_short == "assembly_3":
        s_t = df_t.median(axis=1).fillna(0)
    elif project_name_short == "lancaster":
        s_t = df_t.median(axis=1).fillna(0)
    elif project_name_short == "snipesville_2":
        s_t = df_t[[547, 548, 549, 550]].median(axis=1).fillna(0)
    else:
        # If a column has all zeros, change to null
        for col in df_t.columns:
            if df_t[col].eq(0).all():
                df_t.loc[:, col] = np.nan
        s_t = df_t.median(axis=1).fillna(0)
    s_t.name = "t_amb"

    if "met_station_wind_speed" in df_met.columns.get_level_values(
        "sensor_type_name_short",
    ):
        df_ws = df_met.xs(
            "met_station_wind_speed",
            level="sensor_type_name_short",
            axis=1,
        )
    else:
        df_ws = pd.DataFrame(index=df_met.index)
        df_ws["wind_speed"] = np.nan

    # If a column has all zeros, change to null
    for col in df_ws.columns:
        if df_ws[col].eq(0).all():
            df_ws.loc[:, col] = np.nan
    s_ws = df_ws.median(axis=1).fillna(0)
    s_ws.name = "wind_speed"

    s_cell_temp = pvlib.temperature.sapm_cell(
        poa_global=s_poa,
        temp_air=s_t,
        wind_speed=s_ws,
        a=-3.47,
        b=-0.0594,
        deltaT=3,
    )
    s_cell_temp.name = "t_cell"

    devices = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_type_ids=[params["device_type_id"]],  # type: ignore
    ).models()

    device_id_to_capacity_dc = {
        device.device_id: device.capacity_dc for device in devices
    }

    df_solpos = pvlib.solarposition.get_solarposition(
        time=s_poa.index,
        latitude=location.latitude,
        longitude=location.longitude,
    )

    s_aoi = pvlib.irradiance.aoi(
        surface_tilt=0,  # TODO
        surface_azimuth=180,  # TODO
        solar_zenith=df_solpos["apparent_zenith"],
        solar_azimuth=df_solpos["azimuth"],
    )

    s_iam = pvlib.iam.ashrae(aoi=s_aoi)

    s_g_poa_effective = s_poa * s_iam
    s_g_poa_effective.name = "effective_poa"

    s_list = []
    for device_id in device_id_to_capacity_dc.keys():
        cap = device_id_to_capacity_dc.get(device_id)
        pdc0 = cap * 1000 if cap is not None else 0

        s_pdc = pvlib.pvsystem.pvwatts_dc(
            g_poa_effective=s_g_poa_effective,
            temp_cell=s_cell_temp,
            pdc0=pdc0,
            gamma_pdc=module["gamma_pdc"],
            temp_ref=25,  # NOTE: Using default from documentation
        ) * params.get("scale", 1)
        s_pdc.name = "pdc"

        s_power_ac = pvlib.inverter.pvwatts(
            pdc=s_pdc,
            pdc0=inverter["pdc0"],
            eta_inv_nom=inverter["eta_inv_nom"],
        )
        s_power_ac.name = device_id

        s_list.append(s_power_ac)

    df_power_ac = pd.concat(s_list, axis=1)

    return df_power_ac


def get_project_expected_power(
    *,
    project: models.Project,
    db: Session,
    project_db: Session,
    start: datetime.datetime,
    end: datetime.datetime,
):
    """todo

    Args:
        project: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    project_name_short = project.name_short

    module = vars.MODULE_DATA[vars.PROJECT_DEVICE_MAP[project_name_short]["module"]]
    inverter = vars.INVERTER_DATA[
        vars.PROJECT_DEVICE_MAP[project_name_short]["inverter"]
    ]
    location = vars.PROJECT_LOCATION_MAP[project_name_short]
    params = vars.PROJECT_PARAMS[project_name_short]

    df_met = get_project_dataframe(
        tag_ids=[],
        sensor_type_ids=[
            SensorType.MET_STATION_POA,
            SensorType.MET_STATION_AMBIENT_TEMPERATURE,
            SensorType.MET_STATION_WIND_SPEED,
        ],
        sensor_type_name_shorts=[],
        start=start,
        end=end,
        db=db,
        project_db=project_db,
        project=project,
    )

    df_met.index = pd.to_datetime(df_met.index)
    df_met = df_met.astype(float)

    # POA
    df_poa = df_met.xs("met_station_poa", level="sensor_type_name_short", axis=1)
    df_poa = df_poa[df_poa > 0]  # Remove negative values
    s_poa = df_poa.mean(axis=1).fillna(0)
    s_poa.name = "poa"

    df_t = df_met.xs(
        "met_station_ambient_temperature",
        level="sensor_type_name_short",
        axis=1,
    )

    if project_name_short == "assembly_1":
        s_t = df_t.mean(axis=1).fillna(0)
    elif project_name_short == "assembly_2":
        s_t = df_t[[43, 44, 45]].mean(axis=1).fillna(0)
    elif project_name_short == "assembly_3":
        s_t = df_t.median(axis=1).fillna(0)
    elif project_name_short == "lancaster":
        s_t = df_t.median(axis=1).fillna(0)
    elif project_name_short == "snipesville_2":
        s_t = df_t[[547, 548, 549, 550]].median(axis=1).fillna(0)
    else:
        s_t = df_t.median(axis=1).fillna(0)
    s_t.name = "t_amb"

    if "met_station_wind_speed" in df_met.columns.get_level_values(
        "sensor_type_name_short",
    ):
        df_ws = df_met.xs(
            "met_station_wind_speed",
            level="sensor_type_name_short",
            axis=1,
        )
        s_ws = df_ws.median(axis=1).fillna(0)
        s_ws.name = "wind_speed"
    else:
        s_ws = pd.Series(index=df_met.index)

    s_cell_temp = pvlib.temperature.sapm_cell(
        poa_global=s_poa,
        temp_air=s_t,
        wind_speed=s_ws,
        a=-3.47,
        b=-0.0594,
        deltaT=3,
    )
    s_cell_temp.name = "t_cell"

    df_solpos = pvlib.solarposition.get_solarposition(
        time=s_poa.index,
        latitude=location.latitude,
        longitude=location.longitude,
    )

    s_aoi = pvlib.irradiance.aoi(
        surface_tilt=0,  # TODO
        surface_azimuth=180,  # TODO - in pvlib docs, 180 is south
        solar_zenith=df_solpos["apparent_zenith"],
        solar_azimuth=df_solpos["azimuth"],
    )

    s_iam = pvlib.iam.ashrae(aoi=s_aoi)

    s_g_poa_effective = s_poa * s_iam
    s_g_poa_effective.name = "effective_poa"

    pdc0 = project.capacity_dc * 1000

    s_pdc = pvlib.pvsystem.pvwatts_dc(
        g_poa_effective=s_g_poa_effective,
        temp_cell=s_cell_temp,
        pdc0=pdc0,
        gamma_pdc=module["gamma_pdc"],
        temp_ref=25,  # NOTE: Using default from documentation
    ) * params.get("scale", 1)
    s_pdc.name = "Expected Power DC - Module"

    s_power_ac = pvlib.inverter.pvwatts(
        pdc=s_pdc,
        pdc0=inverter["pdc0"],
        eta_inv_nom=inverter["eta_inv_nom"],
    )
    s_power_ac.name = "Expected Power AC - PCS"

    df_expected_power = pd.DataFrame(index=s_power_ac.index)
    df_expected_power["Expected Power"] = (s_power_ac / 1000).clip(upper=project.poi)

    return df_expected_power
