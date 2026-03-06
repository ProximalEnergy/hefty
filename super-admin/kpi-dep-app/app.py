from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import kpi_pipeline.config as config
import pandas as pd
import streamlit as st
from core.database import with_db
from core.enumerations import KPIType
from kpi_pipeline.config.step_05_upload import kpi_upload_action
from kpi_pipeline.services.client import action_from_list
from sqlalchemy import select, text

from core import models


def get_column_config(*, columns: list[str]) -> dict[str, st.column_config.Column]:
    """Return fixed-width column config, pinning KPI column when supported."""
    try:
        config: dict[str, st.column_config.Column] = {
            col: st.column_config.Column(col, width="small") for col in columns
        }
        if "kpi" in config:
            config["kpi"] = st.column_config.TextColumn(
                "KPI", width="medium", pinned=True
            )
        if "implemented" in config:
            config["implemented"] = st.column_config.CheckboxColumn(
                "Implem.", width="small", pinned=True
            )
        return config
    except TypeError:
        config = {col: st.column_config.Column(col, width="small") for col in columns}
        if "kpi" in config:
            config["kpi"] = st.column_config.TextColumn("KPI", width="medium")
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
                "Sensor Type", width="medium", pinned=True
            )
        return config
    except TypeError:
        config = {col: st.column_config.Column(col, width="small") for col in columns}
        if "sensor_type" in config:
            config["sensor_type"] = st.column_config.TextColumn(
                "Sensor Type", width="medium"
            )
        return config


def get_table_height(*, row_count: int) -> int:
    """Return dataframe height with a slightly larger max cap."""
    min_height_px = 420
    max_height_px = 500
    estimated_height = 56 + max(row_count, 1) * 35
    return max(min_height_px, min(max_height_px, estimated_height))


def get_selected_projects(
    *, selected_projects: list[str], table_columns: list[str]
) -> list[str]:
    """Return selected project columns that exist in a table."""
    table_column_set = set(table_columns)
    return [col for col in selected_projects if col in table_column_set]


def get_presets_file_path() -> Path:
    """Return repo-local presets file path."""
    return Path(__file__).with_name("presets.json")


def load_presets_dict(
    *, file_path: Path
) -> tuple[dict[str, dict[str, list[str]]], str | None]:
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

    presets: dict[str, dict[str, list[str]]] = {}
    for name, value in payload.items():
        if not isinstance(name, str) or not isinstance(value, dict):
            continue
        projects = value.get("projects", [])
        kpis = value.get("kpis", [])
        if not isinstance(projects, list) or not isinstance(kpis, list):
            continue
        presets[name] = {
            "projects": [str(item) for item in projects],
            "kpis": [str(item) for item in kpis],
        }
    return presets, None


def write_presets_dict(
    *, file_path: Path, presets: dict[str, dict[str, list[str]]]
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
    return {int(kpi.value) for kpi in kpi_upload_action.transform.kpi_fields.keys()}


def get_sensor_type_series() -> pd.Series:
    """Return sensor-type mapping from pipeline input keys to IDs."""
    return pd.Series(
        {
            key: value.sensor_type.value
            for key, value in (
                config.step_01_download.time_series.DownloadTimeSeries.value_registry()
            ).items()
        }
        | {
            key: value.sensor_type.value
            for key, value in (
                config.step_01_download.statuses.DownloadStatus.value_registry()
            ).items()
        }
    ).astype(int)


def get_sensor_type_ids_for_kpis(*, kpi_type_ids: list[int]) -> list[int]:
    """Return sensor_type_ids required by selected KPI pipeline outputs."""
    if not kpi_type_ids:
        return []

    pipeline = action_from_list(
        [
            config.Validate.export(),
            config.Calculate.export(),
            config.Aggregate.export(),
            config.kpi_upload_action,
        ]
    )
    expected_inputs = pipeline.expected_inputs(
        outputs=[KPIType(idx).name for idx in kpi_type_ids]
    )

    sensor_type_series = get_sensor_type_series()
    filtered_series = sensor_type_series.reindex(
        sensor_type_series.index.intersection(expected_inputs)
    )
    filtered_series = filtered_series.dropna().astype(int)
    return sorted(set(filtered_series.values.tolist()))


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
    """Load project display and schema names."""
    with with_db(schema="operational") as db:
        rows = db.execute(
            select(models.Project.name_long, models.Project.name_short).order_by(
                models.Project.name_short
            )
        ).all()
    return pd.DataFrame(rows, columns=["project_name", "project_schema"])


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


@st.cache_data(show_spinner=True)
def load_kpi_matrix() -> pd.DataFrame:
    """Load and build KPI-type-by-project matrix from operational tables."""
    with with_db(schema="operational") as db:
        kpi_data_latest_df = pd.read_sql(
            sql=text(
                """
                SELECT
                    project_id,
                    kpi_type_id,
                    MAX(date) AS latest_timestamp
                FROM operational.kpi_data
                GROUP BY project_id, kpi_type_id
                ORDER BY project_id, kpi_type_id
                """
            ),
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
        kpi_data_latest_df,
        on=["project_id", "kpi_type_id"],
        how="left",
    )

    joined_df["kpi"] = joined_df["kpi_name"].fillna("Unknown KPI")
    joined_df["implemented"] = joined_df["kpi_type_id"].isin(
        get_implemented_kpi_type_ids()
    )
    joined_df["latest_timestamp"] = pd.to_datetime(joined_df["latest_timestamp"])

    matrix_df = joined_df.pivot_table(
        index=["kpi", "implemented", "kpi_type_id"],
        columns="project_name",
        values="latest_timestamp",
        aggfunc="max",
    )

    matrix_df = matrix_df.sort_index(level=["kpi", "implemented", "kpi_type_id"])
    matrix_df.columns.name = None

    display_df = matrix_df.reset_index().drop(columns=["kpi_type_id"])
    return display_df


@st.cache_data(show_spinner=False)
def load_kpi_lookup() -> pd.DataFrame:
    """Load KPI lookup with IDs and display names."""
    with with_db(schema="operational") as db:
        return pd.read_sql(
            sql=text(
                """
                SELECT
                    kpi_type_id,
                    name_long AS kpi_name
                FROM operational.kpi_types
                ORDER BY name_long
                """
            ),
            con=db.bind,
        )


@st.cache_data(show_spinner=False)
def load_kpi_instance_status_matrix() -> pd.DataFrame:
    """Load KPI instance status matrix with none/invisible/visible values."""
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
        {True: "visible", False: "invisible"}
    )
    merged_df["instance_status"] = merged_df["instance_status"].fillna("none")

    matrix_df = merged_df.pivot_table(
        index=["kpi_name", "kpi_type_id"],
        columns="project_name",
        values="instance_status",
        aggfunc="first",
    )
    matrix_df = matrix_df.sort_index(level=["kpi_name", "kpi_type_id"])
    matrix_df.columns.name = None
    display_df = matrix_df.reset_index().drop(columns=["kpi_type_id"])
    display_df = display_df.rename(columns={"kpi_name": "kpi"})
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


def main() -> None:
    """Render the KPI type vs project table app."""
    st.set_page_config(page_title="KPI Types vs Projects", layout="wide")
    st.subheader("KPI Dependency Explorer")
    st.caption(
        "Review KPI instance status, latest KPI dates, and supporting sensor "
        "coverage by project."
    )

    if st.sidebar.button("Refresh data"):
        load_projects.clear()
        load_kpi_matrix.clear()
        load_kpi_lookup.clear()
        load_kpi_instance_status_matrix.clear()
        load_sensor_instance_matrix.clear()
        load_sensor_last_date_matrix.clear()
        st.rerun()

    projects_df = load_projects()
    kpi_lookup_df = load_kpi_lookup()
    shared_project_options = projects_df["project_name"].dropna().astype(str).tolist()
    kpi_options = sorted(kpi_lookup_df["kpi_name"].dropna().unique().tolist())

    presets_file_path = get_presets_file_path()
    presets, presets_error = load_presets_dict(file_path=presets_file_path)
    if presets_error is not None:
        st.sidebar.warning(presets_error)

    preset_names = sorted(presets)
    selected_preset_name = st.sidebar.selectbox(
        "Preset",
        options=["", *preset_names],
        format_func=lambda name: name or "(none)",
        key="preset_name",
    )
    selected_preset = presets.get(selected_preset_name, {})
    preset_projects = [
        item
        for item in selected_preset.get("projects", [])
        if item in shared_project_options
    ]
    preset_kpis = [
        item for item in selected_preset.get("kpis", []) if item in kpi_options
    ]
    default_projects = (
        preset_projects if selected_preset_name else shared_project_options
    )
    default_kpis = preset_kpis if selected_preset_name else kpi_options

    selected_shared_projects = st.sidebar.multiselect(
        "Projects (columns)",
        options=shared_project_options,
        default=default_projects,
        key=f"shared_projects::{selected_preset_name or 'all'}",
    )
    selected_kpis = st.sidebar.multiselect(
        "KPI",
        options=kpi_options,
        default=default_kpis,
        key=f"shared_kpis::{selected_preset_name or 'all'}",
    )
    preset_name_input = st.sidebar.text_input(
        "Preset name",
        value=selected_preset_name,
        placeholder="Type preset name",
    )
    save_col, delete_col = st.sidebar.columns(2)
    with save_col:
        save_clicked = st.button("Save", use_container_width=True)
    with delete_col:
        delete_clicked = st.button(
            "Delete",
            use_container_width=True,
            disabled=not selected_preset_name,
        )

    if save_clicked:
        clean_name = preset_name_input.strip()
        if not clean_name:
            st.sidebar.error("Preset name is required.")
        else:
            presets[clean_name] = {
                "projects": selected_shared_projects,
                "kpis": selected_kpis,
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

    if delete_clicked and selected_preset_name:
        if selected_preset_name not in presets:
            st.sidebar.error("Preset not found.")
        else:
            del presets[selected_preset_name]
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

    selected_kpis = [
        item for item in selected_kpis if item in set(kpi_options)
    ]
    selected_shared_projects = [
        item
        for item in selected_shared_projects
        if item in set(shared_project_options)
    ]
    selected_kpi_ids = sorted(
        kpi_lookup_df[kpi_lookup_df["kpi_name"].isin(selected_kpis)]["kpi_type_id"]
        .astype(int)
        .unique()
        .tolist()
    )
    selected_sensor_type_ids = set(
        get_sensor_type_ids_for_kpis(kpi_type_ids=selected_kpi_ids)
    )

    tab_instances, tab_last_date, tab_sensor_instance, tab_sensor = st.tabs(
        [
            "KPI Instances",
            "KPI Last Date",
            "Sensor Type Instance",
            "Sensor Types Last Date",
        ]
    )

    with tab_instances:
        kpi_matrix_df = load_kpi_matrix()
        kpi_status_df = load_kpi_instance_status_matrix()
        matrix_df = kpi_matrix_df
        filtered_df = matrix_df[matrix_df["kpi"].isin(selected_kpis)]
        selected_projects = get_selected_projects(
            selected_projects=selected_shared_projects,
            table_columns=matrix_df.columns.tolist(),
        )
        status_filtered_df = kpi_status_df[kpi_status_df["kpi"].isin(selected_kpis)]
        status_df = status_filtered_df.set_index("kpi").reindex(
            filtered_df["kpi"].tolist()
        )
        status_df = status_df.reset_index(drop=True)
        status_df = status_df.loc[:, selected_projects]

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
                        "visible": "True",
                        "invisible": "False",
                        "none": "(None)",
                    }
                )
                .astype("object")
            )
        styled_instance_df = style_instance_values(
            df=instance_df,
            instance_columns=selected_projects,
        )
        st.dataframe(
            data=styled_instance_df,
            height=get_table_height(row_count=len(instance_df)),
            width="stretch",
            hide_index=True,
            column_config=get_column_config(columns=instance_df.columns.tolist()),
        )

    with tab_last_date:
        kpi_matrix_df = load_kpi_matrix()
        matrix_df = kpi_matrix_df
        filtered_df = matrix_df[matrix_df["kpi"].isin(selected_kpis)]
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
            height=get_table_height(row_count=len(date_df)),
            width="stretch",
            hide_index=True,
            column_config=get_column_config(columns=date_df.columns.tolist()),
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
            height=get_table_height(row_count=len(display_df)),
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
            height=get_table_height(row_count=len(display_df)),
            width="stretch",
            hide_index=True,
            column_config=get_sensor_column_config(columns=display_df.columns.tolist()),
        )


if __name__ == "__main__":
    main()
