from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

import boto3
import pandas as pd
import streamlit as st
from botocore.exceptions import BotoCoreError, ClientError
from core.crud import operational as op_crud
from core.database import with_db
from core.enumerations import KPITypeEnum, ProjectTypeEnum
from dotenv import load_dotenv
from kpi.op.plan import MultiFieldPlan, PipelinePlan, get_plan
from kpi.registry.download.api import DownloadSensor
from kpi.registry.upload.api import UPLOAD
from kpi.schema.api import BasePipeline
from sqlalchemy import select, text

from core import models

STATUS_VISIBLE = "visible"
STATUS_INVISIBLE = "invisible"
STATUS_NONE = "none"

UI_TRUE = "✅"
UI_FALSE = "❌"
UI_NONE = ""


def get_column_config(*, columns: list[str]) -> dict[str, st.column_config.Column]:
    """Return fixed-width column config, pinning KPI column when supported."""
    try:
        config: dict[str, st.column_config.Column] = {
            col: st.column_config.Column(col, width="small") for col in columns
        }
        if "kpi" in config:
            config["kpi"] = st.column_config.TextColumn(
                "KPI", width="large", pinned=True
            )
        if "implemented" in config:
            config["implemented"] = st.column_config.CheckboxColumn(
                "Implem.", width="small", pinned=True
            )
        return config
    except TypeError:
        config = {col: st.column_config.Column(col, width="small") for col in columns}
        if "kpi" in config:
            config["kpi"] = st.column_config.TextColumn("KPI", width="large")
        if "implemented" in config:
            config["implemented"] = st.column_config.CheckboxColumn(
                "Implem.", width="small"
            )
        return config


def get_sensor_column_config(
    *, columns: list[str]
) -> dict[str, st.column_config.Column]:
    """Return fixed-width sensor column config with pinned first column."""
    try:
        config: dict[str, st.column_config.Column] = {
            col: st.column_config.Column(col, width="small") for col in columns
        }
        if "sensor_type" in config:
            config["sensor_type"] = st.column_config.TextColumn(
                "Sensor Type", width="large", pinned=True
            )
        return config
    except TypeError:
        config = {col: st.column_config.Column(col, width="small") for col in columns}
        if "sensor_type" in config:
            config["sensor_type"] = st.column_config.TextColumn(
                "Sensor Type", width="large"
            )
        return config


def get_selected_projects(
    *, selected_projects: list[str], table_columns: list[str]
) -> list[str]:
    """Return selected project columns that exist in a table."""
    table_column_set = set(table_columns)
    return [col for col in selected_projects if col in table_column_set]


def trigger_kpi_backfill_step_function(
    *,
    state_machine_arn: str,
    region_name: str,
    start: date,
    end: date,
    days_per_chunk: int,
    project_name_short_list: list[str],
    kpi_type_ids: list[int],
) -> str:
    """Start the KPI pipeline backfill state machine (API /kpi-backfill equivalent).

    Args:
        state_machine_arn: Step Functions state machine ARN
            (STEP_FUNCTION_ARN_KPI_PIPELINE).
        region_name: AWS region for the Step Functions client (e.g. AWS_S3_REGION).
        start: Inclusive range start (calendar date).
        end: Exclusive range end (calendar date), matching the KPI pipeline fetcher.
        days_per_chunk: Number of days per processing chunk.
        project_name_short_list: Project name_short values for the backfill.
        kpi_type_ids: KPI type IDs to include.
    """
    payload = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "backfill_days": 0,
        "days_per_chunk": days_per_chunk,
        "project_name_short_list": project_name_short_list,
        "kpi_type_ids": kpi_type_ids,
    }
    client = boto3.client("stepfunctions", region_name=region_name)
    try:
        response = client.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps(payload),
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(
            f"Failed to start KPI backfill step function: {exc}"
        ) from exc
    execution_arn = response.get("executionArn")
    if not execution_arn:
        raise RuntimeError("Step Functions returned no executionArn")
    return str(execution_arn)


def step_functions_execution_console_url(*, execution_arn: str) -> str:
    """Build the AWS console URL for a Step Functions execution detail page.

    Args:
        execution_arn: Execution ARN returned by start_execution.
    """
    parts = execution_arn.split(":")
    if len(parts) < 8 or parts[0] != "arn" or parts[2] != "states":
        raise ValueError("Not a Step Functions execution ARN")
    region = parts[3]
    return (
        f"https://{region}.console.aws.amazon.com/states/home"
        f"?region={region}#/v2/executions/details/{execution_arn}"
    )


def get_presets_file_path() -> Path:
    """Return repo-local presets file path."""
    return Path(__file__).with_name("presets.json")


def load_presets_dict(
    *, file_path: Path
) -> tuple[dict[str, dict[str, list[object]]], str | None]:
    """Load presets JSON into a dictionary."""
    if not file_path.exists():
        return {}, None

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, f"Failed to read presets.json: {exc}"

    if not raw_text.strip():
        return {}, None

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return {}, "Invalid presets.json; using empty presets."

    if not isinstance(payload, dict):
        return {}, "Invalid presets format; using empty presets."

    presets: dict[str, dict[str, list[object]]] = {}
    for name, value in payload.items():
        if not isinstance(name, str) or not isinstance(value, dict):
            continue
        projects = value.get("projects", [])
        kpis = value.get("kpis", [])
        if not isinstance(projects, list) or not isinstance(kpis, list):
            continue
        presets[name] = {
            "projects": [str(item) for item in projects],
            "kpis": [int(item) if str(item).isdigit() else str(item) for item in kpis],
        }
    return presets, None


def write_presets_dict(
    *, file_path: Path, presets: dict[str, dict[str, list[object]]]
) -> str | None:
    """Write presets dictionary to JSON."""
    try:
        file_path.write_text(
            json.dumps(presets, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as exc:
        return f"Failed to write presets.json: {exc}"
    return None


def style_project_dates(
    *,
    df: pd.DataFrame,
    project_columns: list[str],
    status_df: pd.DataFrame | None = None,
) -> pd.io.formats.style.Styler:
    """Color project date cells by thresholds and format as YYYY-MM-DD."""
    date_df = df.copy()
    for col in project_columns:
        date_df[col] = pd.to_datetime(date_df[col], errors="coerce")

    today = date.today()
    yellow_cutoff = today - timedelta(days=7)
    green_cutoff = today - timedelta(days=1)

    def color_from_date(value: object) -> str:
        if pd.isna(value):
            return ""
        value_date = pd.Timestamp(value).date()
        if value_date >= green_cutoff:
            return "background-color: hsl(130, 55%, 86%);"
        if value_date >= yellow_cutoff:
            return "background-color: hsl(52, 95%, 85%);"
        return "background-color: hsl(0, 75%, 88%);"

    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    for col in project_columns:
        styles[col] = date_df[col].map(color_from_date)

    if status_df is not None:
        for col in project_columns:
            if col not in status_df.columns:
                continue
            status_styles = status_df[col].map(
                lambda status: {
                    "none": "border: 2px dashed hsl(210, 10%, 55%);",
                    "invisible": "border: 2px solid hsl(35, 90%, 50%);",
                    "visible": "border: 2px solid hsl(130, 55%, 40%);",
                }.get(str(status), "")
            )
            styles[col] = styles[col] + status_styles

    format_map = {
        col: (lambda value: "" if pd.isna(value) else value.strftime("%Y-%m-%d"))
        for col in project_columns
    }
    return date_df.style.apply(lambda _: styles, axis=None).format(
        format_map,
        na_rep="",
    )


def style_instance_values(
    *, df: pd.DataFrame, instance_columns: list[str]
) -> pd.io.formats.style.Styler:
    """Color instance cells by tri-state string value."""
    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    value_to_style = {
        "True": "background-color: hsl(130, 55%, 86%);",
        "False": "background-color: hsl(0, 75%, 88%);",
        "(None)": "color: hsl(210, 8%, 55%);",
    }
    for col in instance_columns:
        styles[col] = df[col].map(lambda value: value_to_style.get(str(value), ""))
    return df.style.apply(lambda _: styles, axis=None)


def get_implemented_kpi_type_ids() -> set[int]:
    """Return configured KPI type IDs that are implemented in upload step."""
    return {int(kpi_model.kpi_type.value) for kpi_model in UPLOAD.values()}


def get_sensor_type_series() -> pd.Series:
    """Return sensor-type mapping from pipeline input keys to IDs."""
    return pd.Series(
        {
            key: value.value.sensor_type.value
            for key, value in DownloadSensor.field_map().items()
        }
    ).astype(int)


def get_sensor_type_ids_for_kpis(*, kpi_type_ids: list[int]) -> list[int]:
    """Return sensor_type_ids required by selected KPI pipeline outputs."""
    if not kpi_type_ids:
        return []
    pipeline = BasePipeline()
    plan = get_plan(pipeline, outputs=[KPITypeEnum(idx).name for idx in kpi_type_ids])

    download_plan = plan.steps.get("download")
    if not isinstance(download_plan, PipelinePlan):
        return []

    sensor_portion = download_plan.steps.get("download_sensor")
    if not isinstance(sensor_portion, MultiFieldPlan):
        return []

    field_map = DownloadSensor.field_map()
    sensor_type_ids = [
        field_map[field_plan.field_name].value.sensor_type.value
        for field_plan in sensor_portion.fields
        if field_plan.field_name in field_map
    ]
    return sorted(set(sensor_type_ids))


def get_all_sensor_type_ids() -> list[int]:
    """Return all sensor type IDs from download time-series/status registries."""
    sensor_type_series = get_sensor_type_series()
    return sorted(set(sensor_type_series.values.tolist()))


def representative_tag_by_sensor_type(
    *, schema: str, sensor_type_ids: list[int], display_name: str
) -> pd.DataFrame:
    """Return representative tag_id by sensor type for a single project schema."""
    with with_db(schema=schema) as db:
        rows = db.execute(
            select(models.Tag.sensor_type_id, models.Tag.tag_id)
            .where(models.Tag.sensor_type_id.is_not(None))
            .where(models.Tag.sensor_type_id.in_(sensor_type_ids))
            .distinct(models.Tag.sensor_type_id)
            .order_by(models.Tag.sensor_type_id, models.Tag.tag_id)
        ).all()

    return pd.DataFrame(rows, columns=["sensor_type_id", display_name])


def latest_times_by_tag_ids(*, schema: str, tag_ids: list[int]) -> dict[int, date]:
    """Return latest timestamp date for each tag_id in a project schema."""
    if not tag_ids:
        return {}
    with with_db(schema=schema) as db:
        rows = db.execute(
            select(
                models.DataTimeseriesLast.tag_id, models.DataTimeseriesLast.time
            ).where(models.DataTimeseriesLast.tag_id.in_(tag_ids))
        ).all()
    return {
        int(tag_id): pd.Timestamp(time_value).date()
        for tag_id, time_value in rows
        if time_value is not None
    }


@st.cache_data(show_spinner=False)
def load_projects() -> pd.DataFrame:
    """Load project display, schema names, and project types."""
    with with_db(schema="operational") as db:
        rows = db.execute(
            select(
                models.Project.name_long,
                models.Project.name_short,
                models.Project.project_type_id,
            ).order_by(models.Project.name_short)
        ).all()
    return pd.DataFrame(
        rows,
        columns=["project_name", "project_schema", "project_type_id"],
    )


def build_sensor_last_date_from_instances(
    *,
    sensor_instance_df: pd.DataFrame,
    selected_projects: list[str],
    project_schema_lookup: dict[str, str],
) -> pd.DataFrame:
    """Build sensor last-date table using representative tag IDs."""
    display_df = sensor_instance_df.loc[
        :, ["sensor_type_id", "sensor_type", *selected_projects]
    ].copy()
    for project_col in selected_projects:
        schema = project_schema_lookup.get(project_col)
        if schema is None:
            display_df[project_col] = pd.NaT
            continue
        tag_series = pd.to_numeric(
            sensor_instance_df[project_col], errors="coerce"
        ).astype("Int64")
        tag_ids = sorted(set(tag_series.dropna().astype(int).tolist()))
        latest_map = latest_times_by_tag_ids(schema=schema, tag_ids=tag_ids)
        display_df[project_col] = tag_series.map(latest_map)
    return display_df


@st.cache_data(show_spinner=True)
def load_sensor_last_date_matrix() -> pd.DataFrame:
    """Load full sensor last-date matrix once using representative tag IDs."""
    sensor_instance_df = load_sensor_instance_matrix()
    projects_df = load_projects()
    project_schema_lookup = dict(
        zip(projects_df["project_name"], projects_df["project_schema"], strict=False)
    )
    project_columns = [
        col
        for col in sensor_instance_df.columns
        if col not in {"sensor_type_id", "sensor_type"}
    ]
    return build_sensor_last_date_from_instances(
        sensor_instance_df=sensor_instance_df,
        selected_projects=project_columns,
        project_schema_lookup=project_schema_lookup,
    )


def _build_kpi_date_matrix(*, use_min_date: bool) -> pd.DataFrame:
    """Build KPI-type-by-project date matrix from operational.kpi_data."""
    kpi_agg_sql = (
        text(
            """
                SELECT
                    project_id,
                    kpi_type_id,
                    MIN(date) AS latest_timestamp
                FROM operational.kpi_data
                GROUP BY project_id, kpi_type_id
                ORDER BY project_id, kpi_type_id
                """
        )
        if use_min_date
        else text(
            """
                SELECT
                    project_id,
                    kpi_type_id,
                    MAX(date) AS latest_timestamp
                FROM operational.kpi_data
                GROUP BY project_id, kpi_type_id
                ORDER BY project_id, kpi_type_id
                """
        )
    )
    with with_db(schema="operational") as db:
        kpi_data_agg_df = pd.read_sql(
            sql=kpi_agg_sql,
            con=db.bind,
        )

        projects_df = pd.read_sql(
            sql=text(
                """
                SELECT
                    project_id,
                    name_long AS project_name
                FROM operational.projects
                """
            ),
            con=db.bind,
        )

        kpi_types_df = pd.read_sql(
            sql=text(
                """
                SELECT
                    kt.kpi_type_id,
                    kt.name_long AS kpi_name
                FROM operational.kpi_types AS kt
                """
            ),
            con=db.bind,
        )

    full_grid_df = kpi_types_df.assign(_key=1).merge(
        projects_df.assign(_key=1),
        on="_key",
        how="inner",
    )
    full_grid_df = full_grid_df.drop(columns="_key")

    joined_df = full_grid_df.merge(
        kpi_data_agg_df,
        on=["project_id", "kpi_type_id"],
        how="left",
    )

    joined_df["kpi"] = joined_df.apply(
        lambda row: (
            f"{row['kpi_name']} ({int(row['kpi_type_id'])})"
            if pd.notna(row["kpi_name"])
            else f"Unknown KPI ({int(row['kpi_type_id'])})"
        ),
        axis=1,
    )
    joined_df["implemented"] = joined_df["kpi_type_id"].isin(
        get_implemented_kpi_type_ids()
    )
    joined_df["latest_timestamp"] = pd.to_datetime(joined_df["latest_timestamp"])

    matrix_df = joined_df.pivot(
        index=["kpi", "implemented", "kpi_type_id"],
        columns="project_name",
        values="latest_timestamp",
    )

    matrix_df = matrix_df.sort_index(level=["kpi", "implemented", "kpi_type_id"])
    matrix_df.columns.name = None

    display_df = matrix_df.reset_index().drop(columns=["kpi_type_id"])
    return display_df


@st.cache_data(show_spinner=True)
def load_kpi_matrix() -> pd.DataFrame:
    """Load and build KPI-type-by-project last-date matrix from operational tables."""
    return _build_kpi_date_matrix(use_min_date=False)


@st.cache_data(show_spinner=True)
def load_kpi_first_date_matrix() -> pd.DataFrame:
    """Load KPI-type-by-project first-date matrix from operational.kpi_data."""
    return _build_kpi_date_matrix(use_min_date=True)


@st.cache_data(show_spinner=False)
def load_kpi_lookup() -> pd.DataFrame:
    """Load KPI lookup with IDs, display names, and project types."""
    with with_db(schema="operational") as db:
        return pd.read_sql(
            sql=text(
                """
                SELECT
                    kpi_type_id,
                    name_long AS kpi_name,
                    project_type_id
                FROM operational.kpi_types
                ORDER BY name_long
                """
            ),
            con=db.bind,
        )


def compute_special_preset(
    *,
    name: str,
    projects_df: pd.DataFrame,
    kpi_lookup_df: pd.DataFrame,
) -> tuple[list[str], list[str]]:
    """Return project names and KPI ID strings for special presets."""
    name = name.strip()
    project_type_map = {
        "[PV]": ProjectTypeEnum.PV.value,
        "[BESS]": ProjectTypeEnum.BESS.value,
        "[PVS]": ProjectTypeEnum.PVS.value,
    }
    if name not in project_type_map:
        return [], []

    project_type_id = project_type_map[name]
    if name == "[PVS]":
        kpi_project_type_ids = {
            ProjectTypeEnum.PV.value,
            ProjectTypeEnum.BESS.value,
            ProjectTypeEnum.PVS.value,
        }
    else:
        kpi_project_type_ids = {project_type_id}

    project_mask = projects_df["project_type_id"] == project_type_id
    project_names = (
        projects_df.loc[project_mask, "project_name"].dropna().astype(str).tolist()
    )

    kpi_mask = kpi_lookup_df["project_type_id"].isin(kpi_project_type_ids)
    kpi_ids = (
        kpi_lookup_df.loc[kpi_mask, "kpi_type_id"]
        .dropna()
        .astype(int)
        .astype(str)
        .tolist()
    )

    return project_names, kpi_ids


_LOAD_MENU_LOGICAL = ("[ALL]", "[BESS]", "[PV]", "[PVS]")


@st.cache_data(show_spinner=False)
def load_kpi_instance_status_with_ids() -> pd.DataFrame:
    """Load row-wise KPI instance status with IDs and tri-state values."""
    with with_db(schema="operational") as db:
        projects_df = pd.read_sql(
            sql=text(
                """
                SELECT
                    project_id,
                    name_long AS project_name
                FROM operational.projects
                """
            ),
            con=db.bind,
        )
        kpi_types_df = pd.read_sql(
            sql=text(
                """
                SELECT
                    kpi_type_id,
                    name_long AS kpi_name
                FROM operational.kpi_types
                """
            ),
            con=db.bind,
        )
        kpi_instances_df = pd.read_sql(
            sql=text(
                """
                SELECT
                    project_id,
                    kpi_type_id,
                    is_visible
                FROM operational.kpi_instances
                """
            ),
            con=db.bind,
        )

    full_grid_df = kpi_types_df.assign(_key=1).merge(
        projects_df.assign(_key=1),
        on="_key",
        how="inner",
    )
    full_grid_df = full_grid_df.drop(columns="_key")
    merged_df = full_grid_df.merge(
        kpi_instances_df,
        on=["project_id", "kpi_type_id"],
        how="left",
    )
    merged_df["instance_status"] = merged_df["is_visible"].map(
        {True: STATUS_VISIBLE, False: STATUS_INVISIBLE}
    )
    merged_df["instance_status"] = merged_df["instance_status"].fillna(STATUS_NONE)

    merged_df["kpi"] = merged_df.apply(
        lambda row: (
            f"{row['kpi_name']} ({int(row['kpi_type_id'])})"
            if pd.notna(row["kpi_name"])
            else f"Unknown KPI ({int(row['kpi_type_id'])})"
        ),
        axis=1,
    )
    return merged_df[
        [
            "kpi",
            "kpi_type_id",
            "project_id",
            "project_name",
            "instance_status",
        ]
    ]


def compute_kpi_instance_diff(
    *,
    original: dict[tuple[UUID, int], bool],
    current: dict[tuple[UUID, int], bool],
) -> tuple[list[tuple[UUID, int, bool]], list[tuple[UUID, int]]]:
    """Return upsert and delete rows between original and current states."""
    upserts: list[tuple[UUID, int, bool]] = []
    deletes: list[tuple[UUID, int]] = []

    for key, value in current.items():
        original_value = original.get(key)
        if original_value is None or original_value != value:
            project_id, kpi_type_id = key
            upserts.append((project_id, kpi_type_id, value))

    for key in original:
        if key not in current:
            project_id, kpi_type_id = key
            deletes.append((project_id, kpi_type_id))

    return upserts, deletes


@st.cache_data(show_spinner=False)
def load_kpi_instance_status_matrix() -> pd.DataFrame:
    """Load KPI instance status matrix with none/invisible/visible values."""
    merged_df = load_kpi_instance_status_with_ids()
    matrix_df = merged_df.pivot_table(
        index=["kpi", "kpi_type_id"],
        columns="project_name",
        values="instance_status",
        aggfunc="first",
    )
    matrix_df = matrix_df.sort_index(level=["kpi", "kpi_type_id"])
    matrix_df.columns.name = None
    display_df = matrix_df.reset_index().drop(columns=["kpi_type_id"])
    return display_df


@st.cache_data(show_spinner=True)
def load_sensor_instance_matrix() -> pd.DataFrame:
    """Load and build sensor-type-by-project representative tag ID matrix."""
    sensor_type_id_list = get_all_sensor_type_ids()
    rows_df = pd.DataFrame({"sensor_type_id": sensor_type_id_list})
    projects_df = load_projects()

    with with_db(schema="operational") as db:
        sensor_types_df = pd.DataFrame(
            db.execute(
                select(models.SensorType.sensor_type_id, models.SensorType.name_long)
                .where(models.SensorType.sensor_type_id.in_(sensor_type_id_list))
                .order_by(models.SensorType.sensor_type_id)
            ).all(),
            columns=["sensor_type_id", "sensor_type_name"],
        )

    for _, project in projects_df.iterrows():
        rows_df = rows_df.merge(
            representative_tag_by_sensor_type(
                schema=project["project_schema"],
                sensor_type_ids=sensor_type_id_list,
                display_name=project["project_name"],
            ),
            on="sensor_type_id",
            how="left",
        )

    rows_df = rows_df.merge(sensor_types_df, on="sensor_type_id", how="left")
    rows_df["sensor_type"] = rows_df.apply(
        lambda row: (
            f"{row['sensor_type_name']} ({int(row['sensor_type_id'])})"
            if pd.notna(row["sensor_type_name"])
            else f"Unknown Sensor ({int(row['sensor_type_id'])})"
        ),
        axis=1,
    )
    rows_df = rows_df.sort_values("sensor_type_id")

    project_columns = projects_df["project_name"].tolist()
    display_df = rows_df[["sensor_type_id", "sensor_type", *project_columns]]
    return display_df


def main_kpi_dep_app() -> None:
    """Render the KPI type vs project table app."""
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
    st.set_page_config(page_title="KPI Types vs Projects", layout="wide")

    if st.sidebar.button("Refresh data"):
        load_projects.clear()
        load_kpi_matrix.clear()
        load_kpi_first_date_matrix.clear()
        load_kpi_lookup.clear()
        load_kpi_instance_status_with_ids.clear()
        load_kpi_instance_status_matrix.clear()
        load_sensor_instance_matrix.clear()
        load_sensor_last_date_matrix.clear()

    projects_df = load_projects()
    kpi_lookup_df = load_kpi_lookup()
    shared_project_options = projects_df["project_name"].dropna().astype(str).tolist()
    kpi_lookup_df = kpi_lookup_df.assign(
        kpi_id_str=kpi_lookup_df["kpi_type_id"].astype(int).astype(str),
        kpi_name=kpi_lookup_df["kpi_name"].astype(str),
    )
    kpi_id_to_name = dict(
        zip(kpi_lookup_df["kpi_id_str"], kpi_lookup_df["kpi_name"], strict=False)
    )
    kpi_id_to_label = {
        kpi_id: f"{kpi_name} ({kpi_id})" for kpi_id, kpi_name in kpi_id_to_name.items()
    }
    kpi_name_to_id = dict(
        zip(kpi_lookup_df["kpi_name"], kpi_lookup_df["kpi_id_str"], strict=False)
    )
    kpi_label_to_id = {label: kpi_id for kpi_id, label in kpi_id_to_label.items()}
    kpi_options = sorted(kpi_id_to_name.keys(), key=int)

    presets_file_path = get_presets_file_path()
    presets, presets_error = load_presets_dict(file_path=presets_file_path)
    if presets_error is not None:
        st.sidebar.warning(presets_error)

    st.session_state.setdefault("kpi_dep_load_id", 0)
    st.session_state.setdefault("kpi_dep_load_mode", "all")

    load_menu = [
        *_LOAD_MENU_LOGICAL,
        *sorted(k for k in presets if k not in _LOAD_MENU_LOGICAL),
    ]
    with st.sidebar.popover("Load"):
        load_choice = st.selectbox(
            "Apply preset", load_menu, label_visibility="collapsed"
        )
        if st.button("Load", key="kpi_dep_load_confirm", use_container_width=True):
            nxt = st.session_state["kpi_dep_load_id"] + 1
            if load_choice == "[ALL]":
                st.session_state["preset_name_field"] = ""
                st.session_state.update(
                    kpi_dep_load_id=nxt,
                    kpi_dep_load_mode="all",
                )
                st.rerun()
            elif load_choice in ("[BESS]", "[PV]", "[PVS]"):
                st.session_state["preset_name_field"] = ""
                st.session_state.update(
                    kpi_dep_load_id=nxt,
                    kpi_dep_load_mode="special",
                    kpi_dep_special_name=load_choice,
                )
                st.rerun()
            else:
                fresh, _ = load_presets_dict(file_path=presets_file_path)
                if load_choice not in fresh:
                    st.warning(f'Preset "{load_choice}" not found in presets file.')
                else:
                    st.session_state.update(
                        kpi_dep_load_id=nxt,
                        kpi_dep_load_mode="json",
                        kpi_dep_json_name=load_choice,
                        preset_name_field=load_choice,
                    )
                    st.rerun()

    load_mode = st.session_state["kpi_dep_load_mode"]
    load_id = st.session_state["kpi_dep_load_id"]
    if load_mode == "all":
        default_projects = shared_project_options
        default_kpis = kpi_options
    elif load_mode == "special":
        sp_name = st.session_state.get("kpi_dep_special_name", "[BESS]")
        pp, pk = compute_special_preset(
            name=sp_name,
            projects_df=projects_df,
            kpi_lookup_df=kpi_lookup_df,
        )
        default_projects = [x for x in pp if x in shared_project_options]
        default_kpis = [x for x in pk if x in kpi_options]
    else:
        jn = st.session_state.get("kpi_dep_json_name", "")
        entry = presets.get(jn, {})
        if entry:
            default_projects = [
                str(x)
                for x in entry.get("projects", [])
                if str(x) in shared_project_options
            ]
            default_kpis: list[str] = []
            for raw in entry.get("kpis", []):
                s = str(raw)
                if s in kpi_options:
                    default_kpis.append(s)
                    continue
                mid = kpi_name_to_id.get(s) or kpi_label_to_id.get(s)
                if mid is not None:
                    default_kpis.append(mid)
            default_kpis = list(dict.fromkeys(default_kpis))
            st.session_state["kpi_dep_json_defaults_p"] = default_projects
            st.session_state["kpi_dep_json_defaults_k"] = default_kpis
        else:
            default_projects = st.session_state.get(
                "kpi_dep_json_defaults_p", shared_project_options
            )
            default_kpis = st.session_state.get("kpi_dep_json_defaults_k", kpi_options)

    _ss_proj = f"shared_projects::{load_id}"
    _ss_kpi = f"shared_kpis::{load_id}"
    _n_sel_proj = (
        len(st.session_state[_ss_proj])
        if _ss_proj in st.session_state
        else len(default_projects)
    )
    _n_sel_kpi = (
        len(st.session_state[_ss_kpi])
        if _ss_kpi in st.session_state
        else len(default_kpis)
    )

    selected_shared_projects = st.sidebar.multiselect(
        f"Projects ({_n_sel_proj})",
        options=shared_project_options,
        default=default_projects,
        key=_ss_proj,
    )
    selected_kpis = st.sidebar.multiselect(
        f"KPIs ({_n_sel_kpi})",
        options=kpi_options,
        default=default_kpis,
        format_func=lambda kpi_id: kpi_id_to_label.get(
            kpi_id, f"Unknown KPI ({kpi_id})"
        ),
        key=_ss_kpi,
    )
    st.sidebar.text_input(
        "Preset name",
        placeholder="Type preset name",
        key="preset_name_field",
    )
    save_col, delete_col = st.sidebar.columns(2)
    with save_col:
        save_clicked = st.button("Save", use_container_width=True)
    with delete_col:
        delete_clicked = st.button("Delete", use_container_width=True)

    if save_clicked:
        clean_name = st.session_state.get("preset_name_field", "").strip()
        if not clean_name:
            st.sidebar.warning("Enter a preset name before saving.")
        elif clean_name in _LOAD_MENU_LOGICAL:
            st.sidebar.warning(
                "That name is reserved for built-in presets and cannot be saved."
            )
        else:
            presets[clean_name] = {
                "projects": selected_shared_projects,
                "kpis": [int(kpi_id) for kpi_id in selected_kpis],
            }
            write_error = write_presets_dict(
                file_path=presets_file_path,
                presets=presets,
            )
            if write_error is not None:
                st.sidebar.error(write_error)
            else:
                st.sidebar.success("Preset saved.")
                st.rerun()

    if delete_clicked:
        clean_name = st.session_state.get("preset_name_field", "").strip()
        if not clean_name:
            st.sidebar.warning("Enter a preset name to delete.")
        elif clean_name in _LOAD_MENU_LOGICAL:
            st.sidebar.error("Cannot delete built-in presets.")
        elif clean_name not in presets:
            st.sidebar.warning("No preset with that exact name exists.")
        else:
            del presets[clean_name]
            write_error = write_presets_dict(
                file_path=presets_file_path,
                presets=presets,
            )
            if write_error is not None:
                st.sidebar.error(write_error)
            else:
                st.sidebar.success("Preset deleted.")
                st.rerun()

    st.sidebar.caption(f"Presets file: `{presets_file_path.name}`")

    selected_kpis = [item for item in selected_kpis if item in set(kpi_options)]
    selected_shared_projects = [
        item for item in selected_shared_projects if item in set(shared_project_options)
    ]
    selected_kpi_ids = sorted({int(kpi_id) for kpi_id in selected_kpis})
    selected_kpi_labels = [
        kpi_id_to_label[kpi_id] for kpi_id in selected_kpis if kpi_id in kpi_id_to_label
    ]
    selected_sensor_type_ids = set(
        get_sensor_type_ids_for_kpis(kpi_type_ids=selected_kpi_ids)
    )

    title_left, title_right = st.columns([4, 1])
    with title_left:
        st.subheader("KPI Dependency Explorer")
        st.caption(
            "Review KPI instance status, latest KPI dates, and supporting sensor "
            "coverage by project."
        )
    with title_right:
        backfill_arn = os.getenv("STEP_FUNCTION_ARN_KPI_PIPELINE")
        backfill_region = os.getenv("AWS_S3_REGION")
        with st.popover("KPI Backfill"):
            st.caption(
                "Uses the projects and KPIs selected in the sidebar. Starts the "
                "same Step Functions run as the web admin KPI backfill tool."
            )
            if not backfill_arn or not backfill_region:
                st.warning(
                    "Set STEP_FUNCTION_ARN_KPI_PIPELINE and AWS_S3_REGION in `.env`."
                )
            _backfill_today = date.today()
            range_value = st.date_input(
                "Date range (last day inclusive)",
                value=(
                    _backfill_today - timedelta(days=7),
                    _backfill_today,
                ),
                max_value=_backfill_today,
                key="kpi_backfill_date_range",
            )
            st.caption(
                "No future calendar dates. Pipeline gets exclusive end = day after "
                "your end date (fetcher: start ≤ d < end)."
            )
            days_chunk = st.number_input(
                "Days per chunk",
                min_value=1,
                value=1,
                step=1,
                key="kpi_backfill_days_chunk",
            )
            st.caption(
                f"Projects: {len(selected_shared_projects)}, "
                f"KPIs: {len(selected_kpi_ids)}"
            )
            trigger_disabled = (
                not backfill_arn
                or not backfill_region
                or not selected_shared_projects
                or not selected_kpi_ids
                or not isinstance(range_value, tuple)
                or len(range_value) != 2
            )
            if st.button(
                "Trigger KPI backfill",
                disabled=trigger_disabled,
                key="kpi_backfill_trigger",
            ):
                start_d, end_d = range_value
                if start_d > end_d:
                    st.error("Start date must be on or before end date.")
                else:
                    long_to_short = dict(
                        zip(
                            projects_df["project_name"].astype(str),
                            projects_df["project_schema"].astype(str),
                            strict=True,
                        )
                    )
                    shorts = [
                        long_to_short[p]
                        for p in selected_shared_projects
                        if p in long_to_short
                    ]
                    if len(shorts) != len(selected_shared_projects):
                        st.error("Could not map every selected project to name_short.")
                    else:
                        try:
                            exec_arn = trigger_kpi_backfill_step_function(
                                state_machine_arn=backfill_arn,
                                region_name=backfill_region,
                                start=start_d,
                                end=end_d + timedelta(days=1),
                                days_per_chunk=int(days_chunk),
                                project_name_short_list=shorts,
                                kpi_type_ids=selected_kpi_ids,
                            )
                        except RuntimeError as exc:
                            st.error(str(exc))
                        else:
                            st.success("KPI backfill accepted.")
                            try:
                                console_url = step_functions_execution_console_url(
                                    execution_arn=exec_arn,
                                )
                            except ValueError:
                                st.code(exec_arn, language=None)
                            else:
                                st.link_button(
                                    "Open execution in AWS console",
                                    console_url,
                                    use_container_width=True,
                                )
                                st.caption(exec_arn)

    (
        tab_instances,
        tab_last_date,
        tab_first_date,
        tab_sensor_instance,
        tab_sensor,
    ) = st.tabs(
        [
            "KPI Instances",
            "KPI Last Date",
            "KPI First Date",
            "Sensor Type Instance",
            "Sensor Types Last Date",
        ]
    )

    with tab_instances:
        kpi_status_df = load_kpi_instance_status_matrix()
        kpi_status_with_ids_df = load_kpi_instance_status_with_ids()
        implemented_lookup = kpi_lookup_df.assign(
            kpi=lambda df: df["kpi_name"] + " (" + df["kpi_id_str"].astype(str) + ")",
            implemented=lambda df: df["kpi_type_id"].isin(
                get_implemented_kpi_type_ids()
            ),
        )[["kpi", "implemented"]].drop_duplicates(subset=["kpi"])
        filtered_df = (
            kpi_status_df[kpi_status_df["kpi"].isin(selected_kpi_labels)]
            .merge(implemented_lookup, on="kpi", how="left")
            .fillna({"implemented": False})
        )
        selected_projects = get_selected_projects(
            selected_projects=selected_shared_projects,
            table_columns=filtered_df.columns.tolist(),
        )
        status_df = filtered_df.loc[:, selected_projects]

        instance_df = pd.DataFrame(
            {
                "kpi": filtered_df["kpi"].reset_index(drop=True),
                "implemented": filtered_df["implemented"].reset_index(drop=True),
            }
        )
        for project_col in selected_projects:
            instance_df[project_col] = (
                status_df[project_col]
                .map(
                    {
                        STATUS_VISIBLE: UI_TRUE,
                        STATUS_INVISIBLE: UI_FALSE,
                        STATUS_NONE: UI_NONE,
                    }
                )
                .fillna(UI_NONE)
                .astype("object")
            )

        filtered_ids_df = kpi_status_with_ids_df[
            kpi_status_with_ids_df["kpi"].isin(selected_kpi_labels)
        ]
        filtered_ids_df = filtered_ids_df[
            filtered_ids_df["project_name"].isin(selected_projects)
        ]
        cell_key_lookup: dict[tuple[str, str], tuple[UUID, int]] = {}
        original_state: dict[tuple[UUID, int], bool] = {}
        for _, row in filtered_ids_df.iterrows():
            key = (row["project_id"], int(row["kpi_type_id"]))
            cell_key_lookup[(str(row["kpi"]), str(row["project_name"]))] = key
            status = str(row["instance_status"])
            if status == STATUS_VISIBLE:
                original_state[key] = True
            elif status == STATUS_INVISIBLE:
                original_state[key] = False

        column_config = get_column_config(columns=instance_df.columns.tolist())
        if "kpi" in column_config:
            column_config["kpi"] = st.column_config.TextColumn(
                "KPI",
                width="large",
                pinned=True,
                disabled=True,
            )
        if "implemented" in column_config:
            column_config["implemented"] = st.column_config.CheckboxColumn(
                "Implem.",
                width="small",
                pinned=True,
                disabled=True,
            )
        for project_col in selected_projects:
            column_config[project_col] = st.column_config.SelectboxColumn(
                project_col,
                options=[UI_NONE, UI_FALSE, UI_TRUE],
            )

        if "kpi_editor_version" not in st.session_state:
            st.session_state["kpi_editor_version"] = 0
        editor_key = f"kpi_instance_editor::{st.session_state['kpi_editor_version']}"

        edited_df = st.data_editor(
            instance_df,
            width="stretch",
            hide_index=True,
            column_config=column_config,
            key=editor_key,
        )

        current_state: dict[tuple[UUID, int], bool] = {}
        for _, row in edited_df.reset_index(drop=True).iterrows():
            kpi_label = str(row["kpi"])
            for project_col in selected_projects:
                cell_key = cell_key_lookup.get((kpi_label, project_col))
                if cell_key is None:
                    continue
                value = str(row[project_col])
                if value == UI_TRUE:
                    current_state[cell_key] = True
                elif value == UI_FALSE:
                    current_state[cell_key] = False

        upserts, deletes = compute_kpi_instance_diff(
            original=original_state,
            current=current_state,
        )
        has_changes = bool(upserts or deletes)

        change_status_label = (
            "Changes detected" if has_changes else "In sync with database"
        )

        apply_col, revert_col, _spacer_col = st.columns([1.5, 1, 6])

        with apply_col:
            if st.button(
                "Apply KPI instance changes",
                disabled=not has_changes,
                help=change_status_label,
            ):
                try:
                    with with_db(schema="operational") as db:
                        op_crud.kpi_instances.bulk_upsert_kpi_instances(
                            db=db,
                            rows=upserts,
                        )
                        op_crud.kpi_instances.bulk_delete_kpi_instances(
                            db=db,
                            rows=deletes,
                        )
                except Exception as exc:
                    st.error(f"Failed to update KPI instances: {exc}")
                else:
                    st.success("KPI instances updated.")
                    load_kpi_instance_status_with_ids.clear()
                    load_kpi_instance_status_matrix.clear()
                    st.rerun()

        with revert_col:
            revert_help = (
                "Revert changes to last saved state"
                if has_changes
                else "No changes to revert"
            )
            if st.button(
                "Revert changes",
                disabled=not has_changes,
                help=revert_help,
            ):
                st.session_state["kpi_editor_version"] += 1
                st.rerun()

        caption_color = "red" if has_changes else "green"
        st.markdown(
            f'<span style="color: {caption_color};">{change_status_label}</span>',
            unsafe_allow_html=True,
        )

    with tab_last_date:
        kpi_matrix_df = load_kpi_matrix()
        matrix_df = kpi_matrix_df
        filtered_df = matrix_df[matrix_df["kpi"].isin(selected_kpi_labels)]
        selected_projects = get_selected_projects(
            selected_projects=selected_shared_projects,
            table_columns=matrix_df.columns.tolist(),
        )
        visible_columns = ["kpi", "implemented", *selected_projects]
        date_df = filtered_df.loc[:, visible_columns].copy()
        for project_col in selected_projects:
            date_df[project_col] = pd.to_datetime(date_df[project_col]).dt.date

        styled_df = style_project_dates(
            df=date_df,
            project_columns=selected_projects,
        )

        st.dataframe(
            data=styled_df,
            width="stretch",
            hide_index=True,
            column_config=get_column_config(columns=date_df.columns.tolist()),
        )

    with tab_first_date:
        first_matrix_df = load_kpi_first_date_matrix()
        filtered_first = first_matrix_df[
            first_matrix_df["kpi"].isin(selected_kpi_labels)
        ]
        selected_projects_first = get_selected_projects(
            selected_projects=selected_shared_projects,
            table_columns=first_matrix_df.columns.tolist(),
        )
        visible_first = ["kpi", "implemented", *selected_projects_first]
        first_date_df = filtered_first.loc[:, visible_first].copy()
        for project_col in selected_projects_first:
            first_date_df[project_col] = pd.to_datetime(
                first_date_df[project_col]
            ).dt.date

        st.dataframe(
            data=first_date_df,
            width="stretch",
            hide_index=True,
            column_config=get_column_config(columns=first_date_df.columns.tolist()),
        )

    with tab_sensor_instance:
        sensor_instance_df = load_sensor_instance_matrix()
        filtered_df = sensor_instance_df[
            sensor_instance_df["sensor_type_id"].isin(selected_sensor_type_ids)
        ]
        selected_projects = get_selected_projects(
            selected_projects=selected_shared_projects,
            table_columns=sensor_instance_df.columns.tolist(),
        )
        visible_columns = ["sensor_type", *selected_projects]
        display_df = filtered_df.loc[:, visible_columns].copy()

        for project_col in selected_projects:
            display_df[project_col] = display_df[project_col].map(
                lambda value: "" if pd.isna(value) else str(int(value))
            )

        st.dataframe(
            data=display_df,
            width="stretch",
            hide_index=True,
            column_config=get_sensor_column_config(columns=display_df.columns.tolist()),
        )

    with tab_sensor:
        sensor_last_date_df = load_sensor_last_date_matrix()
        filtered_df = sensor_last_date_df[
            sensor_last_date_df["sensor_type_id"].isin(selected_sensor_type_ids)
        ]
        selected_projects = get_selected_projects(
            selected_projects=selected_shared_projects,
            table_columns=sensor_last_date_df.columns.tolist(),
        )
        display_df = filtered_df.loc[:, ["sensor_type", *selected_projects]].copy()
        styled_df = style_project_dates(
            df=display_df,
            project_columns=selected_projects,
        )
        st.dataframe(
            data=styled_df,
            width="stretch",
            hide_index=True,
            column_config=get_sensor_column_config(columns=display_df.columns.tolist()),
        )


if __name__ == "__main__":
    main_kpi_dep_app()
