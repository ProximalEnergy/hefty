# --- Imports ---
import asyncio
import logging
from asyncio import Task

import pandas as pd
import polars as pl
import psycopg2
from interfaces import (
    Indeces,
    InverterEquipmentSeries,
    MetDataObserved,
    MetTimeIndex,
    MetTimeSeries,
    ModuleEquipmentSeries,
    QualityAssurance,
    RackingEquipmentSeries,
    SystemSeries,
)
from p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from p01_get_data._utils.validation import save_validation_met_data
from p01_get_data.s00_get_simulation_config import SimulationConfig
from p01_get_data.source_proximal import (
    Inverter,
    Project,
    Racking,
    System,
    calc_axis_azimuth,
    combine_met_and_soiling_data,
    get_db_engine,
    get_environment_variables,
    get_met_data,
    get_met_soiling,
    get_simulation_version,
    log_met_data,
    qa_met_data,
    qc_combined_data,
    qc_soiling_data,
    qc_times,
)
from p01_get_data.source_proximal.s09_get_module_data import Module
from p01_get_data.source_proximal.s09_get_racking_data import Racking


# --- Function ---
async def from_proximal_db(
    cls,
    project_name_short: str,
    simulation_temporal_mode: SimulationTemporalMode,
    simulation_start: str | None = None,
    simulation_end: str | None = None,
    **config_overrides,
):
    """Run from_proximal_db."""
    logging.info("... Get Data")
    # --- Environment Variables ---
    (
        ENVIRONMENT,
        DATABASE_URL,
        AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY,
        AWS_S3_BUCKET_NAME,
    ) = get_environment_variables()

    # --- Simulation Config ---
    simulation_config = SimulationConfig.initialize_with_overrides(**config_overrides)

    # --- QC Times ---
    simulation_start, simulation_end = qc_times(
        simulation_temporal_mode=simulation_temporal_mode.value,
        simulation_start=simulation_start,
        simulation_end=simulation_end,
        ENVIRONMENT=ENVIRONMENT,
    )

    # --- Database Engine ---
    engine = get_db_engine(database_url=DATABASE_URL)

    # --- Project Data ---
    project: Project = await Project.create(
        project_name_short=project_name_short,
    )

    # --- Async Block 1  ---
    try:
        async with asyncio.TaskGroup() as tg:
            met_data_raw_task: Task[pl.DataFrame] = tg.create_task(
                get_met_data(
                    time_zone=project.time_zone,
                    project_name_short=project.name_short,
                    project_data_table_name=project.data_table,
                    engine=engine,
                    ENVIRONMENT=ENVIRONMENT,
                    simulation_temporal_mode=simulation_temporal_mode,
                    simulation_start=simulation_start,
                    simulation_end=simulation_end,
                )
            )
            soiling_data_raw_task: Task[pl.DataFrame] = tg.create_task(
                get_met_soiling(
                    model_soiling=simulation_config.soiling,
                    project_name_short=project_name_short,
                    project_data_table_name=project.data_table,
                    engine=engine,
                    ENVIRONMENT=ENVIRONMENT,
                    simulation_temporal_mode=simulation_temporal_mode,
                    simulation_start=simulation_start,
                    simulation_end=simulation_end,
                    time_zone=project.time_zone,
                )
            )
            system_task: Task[System] = tg.create_task(
                System.create(
                    project_name_short=project_name_short,
                    AWS_S3_BUCKET_NAME=AWS_S3_BUCKET_NAME,
                )
            )
            version_task: Task[str] = tg.create_task(get_simulation_version())

        met_data_raw: pl.DataFrame = met_data_raw_task.result()
        soiling_data_raw = soiling_data_raw_task.result()
        system = system_task.result()
        version = version_task.result()

    except* psycopg2.OperationalError as eg:
        logging.warning(
            "Retryable database connectivity event while loading proximal inputs",
            exc_info=eg,
        )
        raise
    except* Exception as eg:
        for exc in eg.exceptions:
            logging.error(f"Task failed with error: {exc}", exc_info=True)
        raise

    # --- LOGGING ---
    if (project.name_short == "sun_streams_4") & (
        simulation_temporal_mode == SimulationTemporalMode.INSTANTANEOUS
    ):
        log_met_data(
            met_data=met_data_raw,
            soiling_data=soiling_data_raw,
        )

    # --- Sync Block ---
    met_data = qa_met_data(
        met_data_raw=met_data_raw,
        use_poa_only=simulation_config.use_poa_only,
    )
    soiling_data = qc_soiling_data(
        soiling_data_raw=soiling_data_raw,
        soiling_model=simulation_config.soiling,
        use_poa_only=simulation_config.use_poa_only,
    )
    met_data_combined = combine_met_and_soiling_data(
        met_data=met_data,
        soiling_data=soiling_data,
        time_zone=project.time_zone,
    )
    met_data_qc = qc_combined_data(
        combined_data=met_data_combined,
        system=system,
        use_poa_only=simulation_config.use_poa_only,
        use_median_irr_sensor=simulation_config.use_median_irr_sensor,
    )
    met_data_pandas: pd.DataFrame = met_data_qc.to_pandas()
    met_data_pandas = met_data_pandas.loc[
        met_data_pandas["met_name"].isin(pd.Series(system.met_name.unique()))
    ].reset_index()

    # --- VALIDATION ---
    if ENVIRONMENT == "VALIDATE":
        # Perform validation checks here
        target_met_station = "05"
        logging.info(
            f"Saving VALIDATION MET Data:  Target met station: {target_met_station}"
        )
        save_validation_met_data(
            met_data_pandas=met_data_pandas,
            project_name_short=project.name_short,
            simulation_start=simulation_start,
            met_name=target_met_station,
        )

    # --- Async Block 2 ---
    # System data is required for these queries
    async with asyncio.TaskGroup() as tg:
        unique_racking_ids = system.racking_equipment_id.drop_duplicates()
        unique_pcs_ids = system.pcs_equipment_id.drop_duplicates()
        unique_module_ids = system.module_equipment_id.drop_duplicates()

        racking_task = tg.create_task(
            Racking.get_racking_data(
                unique_racking_ids=unique_racking_ids,
            )
        )
        inverters_task = tg.create_task(
            Inverter.get_inverter_data(
                unique_inverter_ids=unique_pcs_ids,
            )
        )
        modules_task = tg.create_task(
            Module.get_module_data(
                unique_module_ids=unique_module_ids,
            )
        )

    rackings = racking_task.result()
    inverters = inverters_task.result()
    modules = modules_task.result()

    axis_azimuth = calc_axis_azimuth(latitude=project.latitude)

    # Populate indeces
    indeces = Indeces(
        met_time_index=MetTimeIndex(met_data_pandas.loc[:, ["time", "met_name"]]),
        string_index=SystemSeries(system.string_id),
        module_equipment_index=ModuleEquipmentSeries(modules.module_equipment_id),
        racking_equipment_index=RackingEquipmentSeries(rackings.racking_equipment_id),
        inverter_equipment_index=InverterEquipmentSeries(inverters.pcs_equipment_id),
        combiner_device_index=system.combiner_device_id,
        inverter_device_index=system.pcs_device_id,
        transformer_device_index=system.transformer_device_id,
    )

    # Populate quality assurance
    quality_assurance = QualityAssurance(
        tier=MetTimeSeries(met_data_pandas.loc[:, "tier"]),
        tier_codes=MetTimeSeries(met_data_pandas.loc[:, "tier_codes"]),
    )

    return cls(
        engine=engine,
        version=version,
        project=project,
        indeces=indeces,
        quality_assurance=quality_assurance,
        met_data=MetDataObserved(met_data=met_data_pandas),
        simulation_config=simulation_config,
        system=system,
        modules=modules,
        rackings=rackings,
        inverters=inverters,
        axis_azimuth=axis_azimuth,
        SIMULATION_TEMPORAL_MODE=simulation_temporal_mode,
        ENVIRONMENT=ENVIRONMENT,
    )
