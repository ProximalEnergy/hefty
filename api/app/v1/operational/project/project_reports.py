import datetime
import mimetypes
import time
from io import BytesIO
from typing import Annotated, Any, cast

import boto3
import numpy as np
import pandas as pd
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import DeviceType, SensorType
from fastapi import APIRouter, Depends, HTTPException
from natsort import natsort_keygen, natsorted
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import utils
from app._crud.operational.cec_pv_inverters import get_cec_pv_inverters
from app._crud.operational.cec_pv_modules import get_cec_pv_modules
from app._crud.operational.pv_modules import get_pv_modules
from app.dependencies import (
    get_project_api,
    get_project_db,
    get_project_db_async,
)
from app.logger import logger
from core import models

router = APIRouter(
    prefix="/reports",
    tags=["project_reports"],
)


@router.get("/pcs-apparent-vs-voltage")
async def get_pcs_apparent_vs_voltage(
    *,
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
    start: datetime.datetime,
    end: datetime.datetime,
):
    """todo

    Args:
        project_db: Description for project_db.
        project: Description for project.
        start: Description for start.
        end: Description for end.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    tags_df = await core.crud.project.tags.get_project_tags_v2(
        sensor_type_ids=[
            SensorType.PV_PCS_AC_APPARENT_POWER,
            SensorType.PV_PCS_VOLTAGE_LL_AB,
            SensorType.PV_PCS_VOLTAGE_LL_BC,
            SensorType.PV_PCS_VOLTAGE_LL_CA,
        ],
    ).get_async(
        output_type=OutputType.PANDAS,
        schema=project_schema,
    )
    if tags_df.empty:
        raise HTTPException(
            status_code=404, detail="No tags found for requested sensor types."
        )
    tags = [
        models.Tag(**cast(dict[str, Any], record))
        for record in tags_df.to_dict("records")
    ]
    tags_df = tags_df.set_index("tag_id")

    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=[t.tag_id for t in tags],
        query_start=start,
        query_end=end,
        project_db=project_db,
    ).get()

    df = data_timeseries_instance.df.to_pandas()
    df = df.set_index("time")
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
    df.columns = df.columns.astype(int)

    apparent_idx = tags_df[tags_df["sensor_type_id"] == 132].index.tolist()
    df_apparent = df.loc[:, apparent_idx]
    df_apparent = df_apparent.rename(
        columns=tags_df.loc[apparent_idx, "device_id"],
    )  # type: ignore

    vab_idx = tags_df[tags_df["sensor_type_id"] == 133].index.tolist()
    vbc_idx = tags_df[tags_df["sensor_type_id"] == 134].index.tolist()
    vca_idx = tags_df[tags_df["sensor_type_id"] == 135].index.tolist()
    rows_to_grab = vab_idx + vbc_idx + vca_idx
    if not rows_to_grab:
        return []
    voltage_items = (
        tags_df.loc[rows_to_grab]  # type: ignore
        .groupby("device_id", group_keys=False)  # type: ignore
        .apply(lambda x: x.index.tolist(), include_groups=False)  # type: ignore
        .to_dict()
    )
    df_voltage = pd.DataFrame(columns=voltage_items.keys(), index=df.index)
    for device_id, tag_ids in voltage_items.items():
        df_voltage.loc[:, device_id] = df.loc[:, tag_ids].mean(axis=1)

    devices_df = await core.crud.project.devices.get_project_devices(
        device_ids=df_voltage.columns.astype(int).tolist()
    ).get_async(
        output_type=OutputType.PANDAS,
        schema=project_schema,
    )
    device_id_to_name = dict(
        zip(
            devices_df["device_id"].astype(int),
            devices_df["name_long"].fillna(""),
        )
    )
    mask = (df_voltage > 10) & (df_apparent > 0.01)
    cec_pv_inverter_ids = list(set(devices_df["cec_pv_inverter_id"].dropna().tolist()))
    await get_cec_pv_inverters(
        cec_pv_inverter_ids=cec_pv_inverter_ids,
    ).get_async(output_type=OutputType.PANDAS)

    out = []
    for col in df_voltage.columns.astype(int):
        out.append(
            {
                "device_id": col,
                "device_name": device_id_to_name[col],
                "x": df_apparent.loc[mask[col]].loc[:, col].values.tolist(),
                "y": df_voltage.loc[mask[col]].loc[:, col].values.tolist(),
            }
        )
    return out


@router.get("/dc-amperage-report-v2")
async def dc_amperage_report_v2(
    *,
    start: datetime.datetime,
    min_poa: float,
    max_poa_1d: float,
    max_poa_std: float,
    rolling_window: int,
    use_poa_1d: bool,
    use_poa_std: bool,
    resample_rate: str = "5min",
    project_db: Session = Depends(get_project_db),
    async_project_db: AsyncSession = Depends(get_project_db_async),
    project: models.Project = Depends(get_project_api),
):
    """todo

    Args:
        start: Description for start.
        min_poa: Description for min_poa.
        max_poa_1d: Description for max_poa_1d.
        max_poa_std: Description for max_poa_std.
        rolling_window: Description for rolling_window.
        use_poa_1d: Description for use_poa_1d.
        use_poa_std: Description for use_poa_std.
        resample_rate: Description for resample_rate.
        project_db: Description for project_db.
        async_project_db: Description for async_project_db.
        project: Description for project.
    """
    logger.info("DC Amperage Report V2 endpoint starting")

    project_tz = project.time_zone
    start = pd.Timestamp(start).tz_convert(None).normalize()
    start_date = start.tz_localize(project_tz)
    end_date = start_date + pd.Timedelta(days=1)

    logger.info("POA tags")
    project_schema = utils.get_project_schema(project_db=project_db)
    poa_tags_df = await core.crud.project.tags.get_project_tags_v2(
        sensor_type_ids=[SensorType.MET_STATION_POA],
    ).get_async(
        output_type=OutputType.PANDAS,
        schema=project_schema,
    )
    poa_tags = [
        models.Tag(**cast(dict[str, Any], record))
        for record in poa_tags_df.to_dict("records")
    ]

    logger.info("POA data")
    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=[t.tag_id for t in poa_tags],
        query_start=start_date,
        query_end=end_date,
        project_db=project_db,
    ).get()

    df_poa = data_timeseries_instance.df.to_pandas()
    df_poa = df_poa.set_index("time")
    df_poa.index = pd.to_datetime(df_poa.index).tz_convert(project.time_zone)
    df_poa.columns = df_poa.columns.astype(int)

    df_poa = df_poa.resample(resample_rate).mean()

    logger.info("POA data processing")
    df_poa = df_poa[df_poa > 10]
    df_poa = df_poa.dropna(how="all", axis=1).dropna(how="all", axis=0)

    df_poa_1d = df_poa.diff() / 5

    df_poa_1d_std = df_poa_1d.std(axis=1)
    if df_poa_1d.shape[1] == 1:
        df_poa_1d_std = df_poa_1d_std.fillna(0)
    df_poa_1d_std = df_poa_1d_std.interpolate().rolling(rolling_window).mean()

    df_poa_1d_val = df_poa_1d.rolling(rolling_window).mean().mean(axis=1).abs()

    df_poa = df_poa[
        (df_poa.mean(axis=1) > min_poa)
        & (df_poa_1d_val < max_poa_1d if use_poa_1d else True)
        & (df_poa_1d_std < max_poa_std if use_poa_std else True)
    ]

    logger.info("CB tags")
    tags_cb_df = await core.crud.project.tags.get_project_tags_v2(
        sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT],
    ).get_async(
        output_type=OutputType.PANDAS,
        schema=project_schema,
    )
    if tags_cb_df.empty:
        raise HTTPException(
            status_code=404,
            detail="No combiner boxes configured for this project",
        )
    tags_cb = [
        models.Tag(**cast(dict[str, Any], record))
        for record in tags_cb_df.to_dict("records")
    ]
    df_tags_cb = tags_cb_df.set_index("tag_id", drop=True)

    logger.info("CB data")
    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=[t.tag_id for t in tags_cb],
        query_start=start_date,
        query_end=end_date,
        project_db=project_db,
    ).get()

    df_cb = data_timeseries_instance.df.to_pandas()
    df_cb = df_cb.set_index("time")
    df_cb.index = pd.to_datetime(df_cb.index).tz_convert(project.time_zone)
    df_cb.columns = df_cb.columns.astype(int)

    logger.info("CB data processing")
    devices_df = await core.crud.project.devices.get_project_devices(
        device_type_ids=[
            DeviceType.PV_PCS,
            DeviceType.MET_STATION,
            DeviceType.PV_DC_COMBINER,
        ],
        deep=False,
    ).get_async(
        output_type=OutputType.PANDAS,
        schema=project_schema,
    )
    devices_df = devices_df.copy()
    devices_df["name_long"] = devices_df["name_long"].fillna("")
    devices_df["name_short"] = devices_df["name_short"].fillna("")

    inv_devices_df = devices_df[
        devices_df["device_type_id"] == DeviceType.PV_PCS
    ].set_index("device_id", drop=True)

    df_cb_report = devices_df[
        devices_df["device_type_id"] == DeviceType.PV_DC_COMBINER
    ].set_index("device_id", drop=True)

    met_devices = devices_df[
        devices_df["device_type_id"] == DeviceType.MET_STATION
    ].to_dict("records")
    cb_devices = df_cb_report.reset_index().to_dict("records")

    pv_dc_combiners_query = core.crud.project.pv_dc_combiners.get_pv_dc_combiners()
    pv_dc_combiners = await pv_dc_combiners_query.get_async(
        schema=project.name_short,
        output_type=OutputType.POLARS,
    )
    cb_device_id_to_modules_per_pv_source_circuit = {
        row["device_id"]: row["modules_per_pv_source_circuit"]
        for row in pv_dc_combiners.iter_rows(named=True)
    }

    if df_cb_report["pv_module_id"].unique().tolist() != [None]:
        pv_modules = await get_pv_modules(
            db=async_project_db,
            pv_module_ids=df_cb_report["pv_module_id"].unique().tolist(),
        )
        pv_modules_df = pd.DataFrame([x.__dict__ for x in pv_modules]).set_index(
            "pv_module_id",
            drop=True,
        )
        df_cb_report["Vmp"] = df_cb_report["pv_module_id"].map(pv_modules_df["vmp"])
        df_cb_report["pmax"] = df_cb_report["pv_module_id"].map(pv_modules_df["pmax"])
    else:
        pv_modules = await get_cec_pv_modules(
            cec_pv_module_ids=df_cb_report["cec_pv_module_id"].unique().tolist(),
        ).get_async(output_type=OutputType.PANDAS)
        pv_modules_df = pv_modules.set_index("cec_pv_module_id", drop=True)
        df_cb_report["Vmp"] = df_cb_report["cec_pv_module_id"].map(
            pv_modules_df["nameplate_vpmax"],
        )
        df_cb_report["pmax"] = df_cb_report["cec_pv_module_id"].map(
            pv_modules_df["nameplate_pmax"],
        )

    df_cb_report = df_cb_report.sort_values(
        "name_long",
        key=lambda x: x.map(natsort_keygen()),
    )

    df_cb_report["strings_per_cb"] = df_cb_report.index.map(
        cb_device_id_to_modules_per_pv_source_circuit,
    )

    df_cb_report["Parent Inverter"] = df_cb_report["parent_device_id"].map(
        inv_devices_df["name_long"],
    )

    df_cb_report["string_Vmp"] = df_cb_report["Vmp"] * df_cb_report["strings_per_cb"]

    df_cb_report["a_nom"] = (
        df_cb_report["capacity_dc"] * 1000 / df_cb_report["string_Vmp"]
    )

    cb_series_means = df_cb.loc[df_poa.index].mean()
    tag_to_device = df_tags_cb.loc[df_cb.columns, "device_id"].to_dict()
    cb_series_means = cb_series_means.rename(index=tag_to_device)
    df_cb_report["a_avg"] = cb_series_means

    df_cb_report["a_norm"] = df_cb_report["a_avg"] / df_cb_report["a_nom"]

    df_cb_report["a_median"] = df_cb_report["Parent Inverter"].map(
        df_cb_report.groupby("Parent Inverter")["a_norm"].median(),
    )
    df_cb_report["a_norm_adj"] = (
        df_cb_report["a_norm"] / df_cb_report["a_median"]
    ).fillna(0)

    df_cb_report["a_median_proj"] = df_cb_report["a_norm"].median()
    df_cb_report["a_norm_proj"] = df_cb_report["a_norm"] / df_cb_report["a_median_proj"]

    logger.info("Preparing for export")
    df_cb_report = df_cb_report.rename(
        columns={
            "name_long": "Combiner Name",
            "capacity_dc": "kW",
            "pmax": "BIN Class",
        },
    )
    df_cb_report = df_cb_report[
        [
            "Parent Inverter",
            "Combiner Name",
            "BIN Class",
            "kW",
            "Vmp",
            "strings_per_cb",
            "string_Vmp",
            "a_nom",
            "a_avg",
            "a_norm",
            "a_median",
            "a_median_proj",
            "a_norm_adj",
            "a_norm_proj",
        ]
    ]

    index_map = (
        df_tags_cb[["device_id", "name_scada"]]
        .set_index("device_id")
        .to_dict()["name_scada"]
    )
    df_cb_report = df_cb_report.rename(index=index_map)
    df_cb_report.index.name = "Combiner SCADA"

    df_return = df_cb_report[
        ["Parent Inverter", "Combiner Name", "a_norm_adj", "a_norm_proj"]
    ].copy()
    df_return["Combiner Name"] = df_return["Combiner Name"].str.split(".").str[1]

    df_return["Combiner Enumeration"] = (
        (df_return.groupby("Parent Inverter").cumcount() + 1).astype(str).str.zfill(2)
    )

    df_return_inv = df_return.pivot(
        index="Combiner Enumeration",
        columns="Parent Inverter",
        values="a_norm_adj",
    )
    df_return_proj = df_return.pivot(
        index="Combiner Enumeration",
        columns="Parent Inverter",
        values="a_norm_proj",
    )

    df_return_inv = df_return_inv.replace([np.nan, np.inf, -np.inf], None)
    df_return_proj = df_return_proj.replace([np.nan, np.inf, -np.inf], None)

    df_punch_list_performance = df_cb_report.loc[
        (df_cb_report["a_norm_adj"] > 1.1)
        | ((df_cb_report["a_norm_adj"] < 0.9) & (df_cb_report["a_norm_adj"] > 0))
        | (df_cb_report["a_norm_adj"] > 1.05)
        | ((df_cb_report["a_norm_adj"] < 0.95) & (df_cb_report["a_norm_adj"] > 0)),
        ["Combiner Name", "a_norm_adj", "a_norm_proj"],
    ]
    df_punch_list_performance = df_punch_list_performance.reset_index(drop=True)
    df_punch_list_performance = df_punch_list_performance.rename(
        columns={
            "a_norm_adj": "Inverter Normalized",
            "a_norm_proj": "Project Normalized",
        },
    )

    punch_list = df_cb_report.loc[
        (df_cb_report["a_norm_proj"] == 0),
        "Combiner Name",
    ].values.tolist()
    punch_list = natsorted(list(set(punch_list)))
    df_punch_list_offline = df_cb_report[
        df_cb_report["Combiner Name"].isin(punch_list)
    ][["Parent Inverter", "Combiner Name"]]

    inverter_combiner_counts = df_cb_report.groupby("Parent Inverter")[
        "Combiner Name"
    ].count()

    offline_combiner_counts = df_punch_list_offline.groupby("Parent Inverter")[
        "Combiner Name"
    ].count()

    offline_inverters = []
    for inverter in inverter_combiner_counts.index:
        total_combiners = inverter_combiner_counts.get(inverter, 0)
        offline_combiners = offline_combiner_counts.get(inverter, 0)
        if total_combiners > 0 and total_combiners == offline_combiners:
            offline_inverters.append(inverter)

    offline_single_combiners = df_punch_list_offline[
        ~df_punch_list_offline["Parent Inverter"].isin(offline_inverters)
    ]["Combiner Name"].values.tolist()
    df_punch_list_offline_invs = pd.DataFrame(
        data={"Combiner": offline_inverters},
    )
    df_punch_list_offline_cbs = pd.DataFrame(
        data={"Combiner": offline_single_combiners},
    )

    df_metadata = pd.DataFrame(
        data={
            "Parameter": [
                "Clearsky Filters",
                "min_poa",
                "max_poa_1d",
                "max_poa_std",
                "rolling_window",
                "start",
                "end",
                "num_periods",
                "Columns in DC Amperage Check",
                "BIN Class",
                "kW",
                "Vmp",
                "strings_per_cb",
                "string_Vmp",
                "a_nom",
                "a_avg",
                "a_norm",
                "a_median",
                "a_median_proj",
                "a_norm_adj",
                "a_norm_proj",
                "Sheet Descriptions",
                "DC Amperage Check",
                "Punch List (Performance)",
                "Punch List (Offline CBs)",
                "Punch List (Offline Invs)",
                "Matrix (Inv)",
                "Matrix (Proj)",
            ],
            "Value": [
                None,
                min_poa,
                max_poa_1d if use_poa_1d else None,
                max_poa_std if use_poa_std else None,
                rolling_window,
                start_date.tz_localize(None),
                end_date.tz_localize(None),
                df_poa.shape[0],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            "Description": [
                None,
                "Minimum POA irradiance for clear sky period",
                "Maximum 1-minute POA first derivative for clear sky period",
                (
                    "Maximum rolling window standard deviation of POA "
                    "irradiance for clear sky period"
                ),
                "Number of 5-minute periods for rolling window",
                "Analysis Start Period",
                "Analysis End Period",
                "Number of 5-minute periods included in analysis after filters",
                None,
                "BIN Class for modules associated with combiner (W)",
                "Nominal DC Power (kW)",
                "Module Vmp (V), retrieved from CEC database",
                "Number of strings per combiner box",
                "String Vmp (Vmp * strings_per_cb)",
                "Nominal string current (A)",
                "Average combiner box current (A)",
                "Combiner box current as a percent of nominal current",
                (
                    "Median value of a_norm as found across combiners in the "
                    "parent inverter"
                ),
                (
                    "Median value of a_norm as found across combiners in the "
                    "entire project"
                ),
                (
                    "Combiner box current as a percent of median current across "
                    "the parent inverter"
                ),
                (
                    "Combiner box current as a percent of median current across "
                    "the entire project"
                ),
                None,
                "Main DC analysis sheet with normalized values for each combiner",
                (
                    "Punch list of combiners which are performing outside of "
                    "acceptance criteria"
                ),
                (
                    "Punch list of combiners which are offline, but whose parent "
                    "inverter is online"
                ),
                "Punch list of parent inverters which have all combiners offline",
                (
                    "Matrix of combiner current as a percent of nominal current "
                    "for each parent inverter (5% threshold)"
                ),
                (
                    "Matrix of combiner current as a percent of median current "
                    "for entire project (10% threshold)"
                ),
            ],
        },
    )

    def highlight_style(*, val, col, subset: bool = False):
        """todo

        Args:
            val: Description for val.
            col: Description for col.
            subset: Description for subset.
        """
        if subset:
            if col == "a_norm_proj":
                if val > 1.1:
                    return "background-color: #60497A; color: #FFFFFF;"
                if val < 0.9:
                    return "background-color: #FFC7CE; color: #9C0006;"
            elif col == "a_norm_adj":
                if val > 1.05:
                    return "background-color: #60497A; color: #FFFFFF;"
                if val < 0.95:
                    return "background-color: #FFC7CE; color: #9C0006;"
            return ""
        try:
            if val > 1.05:
                return "background-color: #60497A; color: #FFFFFF;"
            if val < 0.95:
                return "background-color: #FFC7CE; color: #9C0006;"
            return ""
        except TypeError:
            return ""

    logger.info("Excel writing")
    excel_buffer = BytesIO()
    poa_buffer = BytesIO()
    cb_buffer = BytesIO()

    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        workbook = writer.book

        bold_center_grey_format = workbook.add_format(
            {"bold": True, "align": "center", "bg_color": "#D3D3D3"},
        )

        df_metadata.to_excel(
            writer,
            sheet_name="Analysis Metadata",
            index=False,
            header=True,
        )
        df_cb_report.style.apply(
            lambda x: [
                highlight_style(val=v, col=col, subset=True)
                for v, col in zip(x, x.index)
            ],
            subset=["a_norm_proj", "a_norm_adj"],
            axis=1,
        ).to_excel(writer, sheet_name="DC Amperage Check", index=True)
        df_punch_list_performance.to_excel(
            writer,
            sheet_name="Punch List (Performance)",
            index=True,
        )
        df_punch_list_offline_cbs.to_excel(
            writer,
            sheet_name="Punch List (Offline CBs)",
            index=True,
        )
        df_punch_list_offline_invs.to_excel(
            writer,
            sheet_name="Punch List (Offline Invs)",
            index=True,
        )
        df_return_inv.style.apply(
            lambda x: [highlight_style(val=v, col=col) for v, col in zip(x, x.index)],
        ).to_excel(writer, sheet_name="Matrix (Inv)", index=True)
        df_return_proj.style.apply(
            lambda x: [highlight_style(val=v, col=col) for v, col in zip(x, x.index)],
        ).to_excel(writer, sheet_name="Matrix (Proj)", index=True)

        meta_sheet = writer.sheets["Analysis Metadata"]

        meta_sheet.merge_range(
            1,
            0,
            1,
            2,
            df_metadata.iloc[0, 0],
            bold_center_grey_format,
        )
        meta_sheet.merge_range(
            9,
            0,
            9,
            2,
            df_metadata.iloc[8, 0],
            bold_center_grey_format,
        )
        meta_sheet.merge_range(
            22,
            0,
            22,
            2,
            df_metadata.iloc[21, 0],
            bold_center_grey_format,
        )

        auto_fit_sheets = {
            "DC Amperage Check": df_cb_report,
            "Punch List (Performance)": df_punch_list_performance,
            "Punch List (Offline CBs)": df_punch_list_offline_cbs,
            "Punch List (Offline Invs)": df_punch_list_offline_invs,
            "Analysis Metadata": df_metadata,
        }
        for sheet_name, dataframe in auto_fit_sheets.items():
            worksheet = writer.sheets[sheet_name]
            for idx, col in enumerate(dataframe.columns):
                series = dataframe[col]
                max_len = (
                    max(series.astype(str).map(len).max(), len(str(series.name))) + 2
                )
                worksheet.set_column(idx, idx, max_len)

    def rename_poa_columns(*, df_poa, poa_tags, met_devices):
        """todo

        Args:
            df_poa: Description for df_poa.
            poa_tags: Description for poa_tags.
            met_devices: Description for met_devices.
        """
        tag_to_device_id = {tag.tag_id: tag.device_id for tag in poa_tags}
        device_id_to_name_short = {
            int(device["device_id"]): device.get("name_short") for device in met_devices
        }

        new_columns = [
            (
                f"Met Station POA {device_id_to_name_short[tag_to_device_id[col]]}"
                if col in tag_to_device_id
                and tag_to_device_id[col] in device_id_to_name_short
                else f"Unknown POA {col}"
            )
            for col in df_poa.columns
        ]

        return df_poa.rename(
            columns={x: y for x, y in zip(df_poa.columns, new_columns)},
        )

    def rename_cb_columns(*, df_cb, cb_devices):
        """todo

        Args:
            df_cb: Description for df_cb.
            cb_devices: Description for cb_devices.
        """
        tag_to_device_id = {tag.tag_id: tag.device_id for tag in tags_cb}
        device_id_to_name_long = {
            int(device["device_id"]): device.get("name_long") for device in cb_devices
        }

        new_columns = [
            (
                f"Combiner Current {device_id_to_name_long[tag_to_device_id[col]]}"
                if col in tag_to_device_id
                and tag_to_device_id[col] in device_id_to_name_long
                else f"Unknown Combiner {col}"
            )
            for col in df_cb.columns
        ]

        return df_cb.rename(columns={x: y for x, y in zip(df_cb.columns, new_columns)})

    df_poa = rename_poa_columns(
        df_poa=df_poa,
        poa_tags=poa_tags,
        met_devices=met_devices,
    )
    df_poa.columns = pd.Index(natsorted(df_poa.columns))

    df_cb = rename_cb_columns(df_cb=df_cb, cb_devices=cb_devices)
    df_cb.columns = pd.Index(natsorted(df_cb.columns))

    def upload_to_s3_and_generate_url(
        *,
        s3_client,
        buffer,
        bucket_name,
        prefix,
        filename,
        tags="temporary",
    ):
        """todo

        Args:
            s3_client: Description for s3_client.
            buffer: Description for buffer.
            bucket_name: Description for bucket_name.
            prefix: Description for prefix.
            filename: Description for filename.
            tags: Description for tags.
        """
        buffer.seek(0)
        file_content = buffer.read()

        file_key = f"{prefix}/{filename}"

        content_type, _ = mimetypes.guess_type(filename)
        if content_type is None:
            content_type = "application/octet-stream"

        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=file_content,
                ContentType=content_type,
                Tagging=tags,
            )

            content_disposition = f'attachment; filename="{filename}"'

            presigned_url = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket_name,
                    "Key": file_key,
                    "ResponseContentDisposition": content_disposition,
                },
                ExpiresIn=3600,
            )
            return presigned_url
        except Exception:
            logger.exception("Error uploading %s to S3", filename)
            return None

    async def process_files(
        *,
        excel_buffer,
        poa_buffer,
        cb_buffer,
        df_poa,
        df_cb,
        project,
        start_date,
    ):
        """todo

        Args:
            excel_buffer: Description for excel_buffer.
            poa_buffer: Description for poa_buffer.
            cb_buffer: Description for cb_buffer.
            df_poa: Description for df_poa.
            df_cb: Description for df_cb.
            project: Description for project.
            start_date: Description for start_date.
        """
        df_poa.to_csv(poa_buffer)
        df_cb.loc[df_poa.index].to_csv(cb_buffer)

        s3_client = boto3.client("s3", region_name="us-east-2")
        bucket_name = "proximal-am-documents"
        prefix = "reports"

        date_str = start_date.strftime("%Y-%m-%d")
        file_stamp = round(time.time())
        excel_filename = (
            f"{project.name_short}_dc_amperage_report_{date_str}_{file_stamp}.xlsx"
        )
        poa_filename = f"{project.name_short}_poa_report_{date_str}_{file_stamp}.csv"
        cb_filename = f"{project.name_short}_cb_report_{date_str}_{file_stamp}.csv"
        files = {
            "excel": {"buffer": excel_buffer, "filename": excel_filename},
            "poa": {"buffer": poa_buffer, "filename": poa_filename},
            "cb": {"buffer": cb_buffer, "filename": cb_filename},
        }

        presigned_urls = {}
        for key, file in files.items():
            presigned_urls[key] = upload_to_s3_and_generate_url(
                s3_client=s3_client,
                buffer=file["buffer"],
                bucket_name=bucket_name,
                prefix=prefix,
                filename=file["filename"],
            )

        return presigned_urls

    presigned_urls = await process_files(
        excel_buffer=excel_buffer,
        poa_buffer=poa_buffer,
        cb_buffer=cb_buffer,
        df_poa=df_poa,
        df_cb=df_cb,
        project=project,
        start_date=start_date,
    )

    logger.info("Return")
    return {
        "inv": df_return_inv.to_dict(orient="split"),
        "proj": df_return_proj.to_dict(orient="split"),
        "reports": presigned_urls,
    }
