import json
import logging
from collections.abc import Iterable
from dataclasses import fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import p03_export.c_export as c_export
import pandas as pd
import pytz
import sqlalchemy
from interfaces import (
    Indeces,
    InverterDeviceSeries,
    InverterEquipmentSeries,
    MetDataObserved,
    MetTimeIndex,
    MetTimeSeries,
    ModuleEquipmentSeries,
    QualityAssurance,
    RackingEquipmentSeries,
    SystemSeries,
    TransformerDeviceSeries,
)
from p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from p01_get_data.class_simulation_inputs import SimulationInputs
from p01_get_data.s00_get_simulation_config import SimulationConfig
from p01_get_data.source_proximal.s03_get_project import PvEemProject
from p01_get_data.source_proximal.s04_get_system_data import System
from p01_get_data.source_proximal.s09_get_inverter_data import Inverter
from p01_get_data.source_proximal.s09_get_module_data import Module
from p01_get_data.source_proximal.s09_get_racking_data import Racking
from p02_simulation.p4_dc_iv.s02_single_diode_params import ModelSingleDiode
from p03_export.s00_simulation_level import SimulationLevel

logger = logging.getLogger(__name__)

PVSYST_REQUIRED_MODULE_COLUMNS = (
    "r_shunt_0",
    "r_shunt_exponent",
    "diode_ideality_factor",
    "diode_ideality_factor_temp_coefficient",
)
PVSYST_SNAPSHOT_ERROR = (
    "Snapshot incompatible with PVSyst, check database and recapture"
)


def _artifacts_root() -> Path:
    return Path(__file__).resolve().parent / "_artifacts"


def _serialize_simulation_config(simulation_config: Any) -> dict[str, Any]:
    if is_dataclass(simulation_config):
        values = {
            field.name: getattr(simulation_config, field.name)
            for field in fields(simulation_config)
        }
    else:
        values = vars(simulation_config)

    return {
        key: (value.value if hasattr(value, "value") else value)
        for key, value in values.items()
    }


def _get_snapshot_dir_path(*, snapshot_name: str) -> Path:
    return _artifacts_root() / "snapshots" / snapshot_name


def _get_snapshot_metadata_path_loc(*, snapshot_name: str) -> Path:
    return _get_snapshot_dir_path(snapshot_name=snapshot_name) / "metadata.json"


def _get_snapshot_table_path_loc(*, snapshot_name: str, file_name: str) -> Path:
    return _get_snapshot_dir_path(snapshot_name=snapshot_name) / file_name


def _is_snapshot_complete(*, snapshot_name: str) -> bool:
    required_files = [
        "metadata.json",
        "indeces_met_time_index.parquet",
        "indeces_string_index.parquet",
        "indeces_module_equipment_index.parquet",
        "indeces_racking_equipment_index.parquet",
        "indeces_inverter_equipment_index.parquet",
        "indeces_combiner_device_index.parquet",
        "indeces_inverter_device_index.parquet",
        "indeces_transformer_device_index.parquet",
        "quality_assurance.parquet",
        "met_data.parquet",
        "system.parquet",
        "modules.parquet",
        "rackings.parquet",
        "inverters.parquet",
    ]
    snapshot_dir = _get_snapshot_dir_path(snapshot_name=snapshot_name)
    if not snapshot_dir.exists():
        return False

    for file_name in required_files:
        if not (snapshot_dir / file_name).exists():
            return False
    return True


def _read_snapshot_metadata(*, snapshot_name: str) -> dict[str, Any]:
    metadata_path = _get_snapshot_metadata_path_loc(snapshot_name=snapshot_name)
    if not metadata_path.exists():
        raise FileNotFoundError(
            "Missing snapshot metadata at "
            f"_tests/_artifacts/snapshots/{snapshot_name}/metadata.json. "
            "Generate this file once before running this test."
        )

    with metadata_path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def _read_snapshot_table(*, snapshot_name: str, file_name: str) -> pd.DataFrame:
    table_path = _get_snapshot_table_path_loc(
        snapshot_name=snapshot_name,
        file_name=file_name,
    )
    if not table_path.exists():
        raise FileNotFoundError(
            "Missing snapshot table at "
            f"_tests/_artifacts/snapshots/{snapshot_name}/{file_name}. "
            "Generate this file once before running this test."
        )
    return pd.read_parquet(table_path)


def save_snapshot_inputs(
    *, snapshot_name: str, simulation_inputs: SimulationInputs
) -> None:
    """Save simulation inputs to a snapshot directory."""
    snapshot_dir = _get_snapshot_dir_path(snapshot_name=snapshot_name)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Metadata
    metadata = {
        "ENVIRONMENT": simulation_inputs.ENVIRONMENT,
        "SIMULATION_TEMPORAL_MODE": simulation_inputs.SIMULATION_TEMPORAL_MODE.value,
        "axis_azimuth": simulation_inputs.axis_azimuth,
        "project": {
            "cod": str(simulation_inputs.project.cod),
            "data_table": simulation_inputs.project.data_table,
            "elevation": simulation_inputs.project.elevation,
            "latitude": simulation_inputs.project.latitude,
            "longitude": simulation_inputs.project.longitude,
            "name_long": simulation_inputs.project.name_long,
            "name_short": simulation_inputs.project.name_short,
            "poi_limit": simulation_inputs.project.poi_limit,
            "time_zone": simulation_inputs.project.time_zone,
        },
        "simulation_config": _serialize_simulation_config(
            simulation_inputs.simulation_config
        ),
        "version": simulation_inputs.version,
    }
    with _get_snapshot_metadata_path_loc(snapshot_name=snapshot_name).open("w") as f:
        json.dump(metadata, f, indent=2)

    # Table saving
    # Indeces
    simulation_inputs.indeces.met_time_index.to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="indeces_met_time_index.parquet",
        )
    )
    pd.DataFrame({"string_id": simulation_inputs.indeces.string_index}).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="indeces_string_index.parquet",
        )
    )
    pd.DataFrame(
        {"module_equipment_id": simulation_inputs.indeces.module_equipment_index}
    ).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="indeces_module_equipment_index.parquet",
        )
    )
    pd.DataFrame(
        {"racking_equipment_id": simulation_inputs.indeces.racking_equipment_index}
    ).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="indeces_racking_equipment_index.parquet",
        )
    )
    pd.DataFrame(
        {"pcs_equipment_id": simulation_inputs.indeces.inverter_equipment_index}
    ).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="indeces_inverter_equipment_index.parquet",
        )
    )
    pd.DataFrame(
        {"combiner_device_id": simulation_inputs.indeces.combiner_device_index}
    ).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="indeces_combiner_device_index.parquet",
        )
    )
    pd.DataFrame(
        {"pcs_device_id": simulation_inputs.indeces.inverter_device_index}
    ).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="indeces_inverter_device_index.parquet",
        )
    )
    pd.DataFrame(
        {"transformer_device_id": simulation_inputs.indeces.transformer_device_index}
    ).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="indeces_transformer_device_index.parquet",
        )
    )

    # QA
    pd.DataFrame(
        {
            "tier": simulation_inputs.quality_assurance.tier,
            "tier_codes": simulation_inputs.quality_assurance.tier_codes,
        }
    ).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="quality_assurance.parquet",
        )
    )

    # Met Data
    met_data_dict = {
        "met_name": simulation_inputs.met_data.met_name,
        "ambient_temperature": simulation_inputs.met_data.ambient_temperature,
        "ghi": simulation_inputs.met_data.ghi,
        "poa": simulation_inputs.met_data.poa,
        "poa_tilt": simulation_inputs.met_data.poa_tilt,
        "relative_humidity": simulation_inputs.met_data.relative_humidity,
        "wind_speed": simulation_inputs.met_data.wind_speed,
        "soil_percent": simulation_inputs.met_data.soil_percent,
    }
    pd.DataFrame(met_data_dict).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="met_data.parquet",
        )
    )

    # System
    system_data_dict = {
        "string_id": simulation_inputs.system.string_id,
        "module_equipment_id": simulation_inputs.system.module_equipment_id,
        "modules_per_string": simulation_inputs.system.modules_per_string,
        "strings_per_combiner": simulation_inputs.system.strings_per_combiner,
        "dc_line_to_combiner_stc": simulation_inputs.system.dc_line_to_combiner_stc,
        "combiner_device_id": simulation_inputs.system.combiner_device_id,
        "racking_controls_gcr": simulation_inputs.system.racking_controls_gcr,
        "racking_equipment_id": simulation_inputs.system.racking_equipment_id,
        "racking_device_id": simulation_inputs.system.racking_device_id,
        "dc_line_to_inverter_stc": simulation_inputs.system.dc_line_to_inverter_stc,
        "pcs_equipment_id": simulation_inputs.system.pcs_equipment_id,
        "pcs_device_id": simulation_inputs.system.pcs_device_id,
        "transformer_equipment_id": simulation_inputs.system.transformer_equipment_id,
        "transformer_device_id": simulation_inputs.system.transformer_device_id,
        "block_device_id": simulation_inputs.system.block_device_id,
        "circuit_device_id": simulation_inputs.system.circuit_device_id,
        "met_name": simulation_inputs.system.met_name,
    }
    pd.DataFrame(system_data_dict).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="system.parquet",
        )
    )

    # Modules
    module_data_dict = {
        "module_equipment_id": simulation_inputs.modules.module_equipment_id,
        # UUID values must be serialized to strings for parquet compatibility.
        "company_id": simulation_inputs.modules.company_id.astype(str),
        "manufacturer": simulation_inputs.modules.manufacturer,
        "model": simulation_inputs.modules.model,
        "family": simulation_inputs.modules.family,
        "technology": simulation_inputs.modules.technology,
        "bifaciality_factor": simulation_inputs.modules.bifaciality_factor,
        "pmax": simulation_inputs.modules.pmax,
        "isc": simulation_inputs.modules.isc,
        "voc": simulation_inputs.modules.voc,
        "imp": simulation_inputs.modules.imp,
        "vmp": simulation_inputs.modules.vmp,
        "efficiency": simulation_inputs.modules.efficiency,
        "gamma_pmax": simulation_inputs.modules.gamma_pmax,
        "alpha_isc": simulation_inputs.modules.alpha_isc,
        "beta_voc": simulation_inputs.modules.beta_voc,
        "warranted_degradation_rate": (
            simulation_inputs.modules.warranted_degradation_rate
        ),
        "warranted_degradation_initial": (
            simulation_inputs.modules.warranted_degradation_initial
        ),
        "length": simulation_inputs.modules.length,
        "width": simulation_inputs.modules.width,
        "area": simulation_inputs.modules.area,
        "frame_overhang": simulation_inputs.modules.frame_overhang,
        "has_ar_coating": simulation_inputs.modules.has_ar_coating,
        "half_cut": simulation_inputs.modules.half_cut,
        "cells_in_series": simulation_inputs.modules.cells_in_series,
        "photocurrent": simulation_inputs.modules.photocurrent,
        "diode_saturation_current": simulation_inputs.modules.diode_saturation_current,
        "r_series": simulation_inputs.modules.r_series,
        "r_shunt": simulation_inputs.modules.r_shunt,
        "r_shunt_0": simulation_inputs.modules.r_shunt_0,
        "r_shunt_exponent": simulation_inputs.modules.r_shunt_exponent,
        "diode_ideality_factor": simulation_inputs.modules.diode_ideality_factor,
        "diode_ideality_factor_temp_coefficient": (
            simulation_inputs.modules.diode_ideality_factor_temp_coefficient
        ),
        "modified_ideality_factor": simulation_inputs.modules.modified_ideality_factor,
        "eg": simulation_inputs.modules.eg,
        "degdt": simulation_inputs.modules.degdt,
        "data_source": simulation_inputs.modules.data_source,
    }
    pd.DataFrame(module_data_dict).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="modules.parquet",
        )
    )

    # Rackings
    racking_data_dict = {
        "racking_equipment_id": simulation_inputs.rackings.racking_equipment_id,
        "racking_type_id": simulation_inputs.rackings.racking_type_id,
        "manufacturer": simulation_inputs.rackings.manufacturer,
        "model": simulation_inputs.rackings.model,
        "max_rotation_angle": simulation_inputs.rackings.max_rotation_angle,
        "min_rotation_angle": simulation_inputs.rackings.min_rotation_angle,
        "pile_height": simulation_inputs.rackings.pile_height,
        "structure_shading_factor": simulation_inputs.rackings.structure_shading_factor,
        "rear_mismatch_factor": simulation_inputs.rackings.rear_mismatch_factor,
    }
    pd.DataFrame(racking_data_dict).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="rackings.parquet",
        )
    )

    # Inverters
    inverter_data_dict = {
        "pcs_equipment_id": simulation_inputs.inverters.pcs_equipment_id,
        "manufacturer": simulation_inputs.inverters.manufacturer,
        "model": simulation_inputs.inverters.model,
        "voltage_mpp_min": simulation_inputs.inverters.voltage_mpp_min,
        "voltage_mpp_max": simulation_inputs.inverters.voltage_mpp_max,
        "voltage_start_up": simulation_inputs.inverters.voltage_start_up,
        "voltage_min": simulation_inputs.inverters.voltage_min,
        "voltage_max": simulation_inputs.inverters.voltage_max,
        "current_max": simulation_inputs.inverters.current_max,
        "power_max_at_reference_temp": [
            x.tolist() for x in simulation_inputs.inverters.power_max_at_reference_temp
        ],
        "reference_temp": [
            x.tolist() for x in simulation_inputs.inverters.reference_temp
        ],
        "voltage_nominal_efficiency": [
            x.tolist() for x in simulation_inputs.inverters.voltage_nominal_efficiency
        ],
        "efficiency_at_low_voltage": [
            x.tolist() for x in simulation_inputs.inverters.efficiency_at_low_voltage
        ],
        "efficiency_at_mid_voltage": [
            x.tolist() for x in simulation_inputs.inverters.efficiency_at_mid_voltage
        ],
        "efficiency_at_high_voltage": [
            x.tolist() for x in simulation_inputs.inverters.efficiency_at_high_voltage
        ],
        "power_start_up": simulation_inputs.inverters.power_start_up,
        "power_ac_nominal": simulation_inputs.inverters.power_ac_nominal,
        "power_dc_nominal": simulation_inputs.inverters.power_dc_nominal,
        "voltage_dc_nominal": simulation_inputs.inverters.voltage_dc_nominal,
        "c0": simulation_inputs.inverters.c0,
        "c1": simulation_inputs.inverters.c1,
        "c2": simulation_inputs.inverters.c2,
        "c3": simulation_inputs.inverters.c3,
        "night_tare": simulation_inputs.inverters.night_tare,
    }
    pd.DataFrame(inverter_data_dict).to_parquet(
        _get_snapshot_table_path_loc(
            snapshot_name=snapshot_name,
            file_name="inverters.parquet",
        )
    )


def _extract_series(*, data_frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in data_frame:
        raise KeyError(f"Missing column '{column}' in snapshot table.")
    return data_frame.loc[:, column]


def _extract_optional_series(*, data_frame: pd.DataFrame, column: str) -> pd.Series:
    if column in data_frame:
        return data_frame.loc[:, column]
    return pd.Series(index=data_frame.index, dtype="float64", name=column)


def _raise_for_incompatible_pvsyst_snapshot(
    *, simulation_inputs: SimulationInputs
) -> None:
    if (
        simulation_inputs.simulation_config.single_diode_model
        != ModelSingleDiode.PVSYST
    ):
        return

    missing_values = any(
        getattr(simulation_inputs.modules, column).isna().any()
        for column in PVSYST_REQUIRED_MODULE_COLUMNS
    )
    if missing_values:
        raise ValueError(PVSYST_SNAPSHOT_ERROR)


def _map_to_numpy_array(*, value: Any) -> Any:
    if isinstance(value, list):
        return np.array(value)
    return value


def read_snapshot_inputs(
    *,
    snapshot_name: str,
    simulation_start: str | None = None,
    simulation_end: str | None = None,
) -> SimulationInputs:
    snapshot_metadata = _read_snapshot_metadata(snapshot_name=snapshot_name)

    project_data = snapshot_metadata["project"]
    project = object.__new__(PvEemProject)
    project.name_short = project_data["name_short"]
    project.name_long = project_data["name_long"]
    project.data_table = project_data["data_table"]
    project.time_zone = project_data["time_zone"]
    project.poi_limit = project_data["poi_limit"]
    project.longitude = project_data["longitude"]
    project.latitude = project_data["latitude"]
    project.elevation = project_data["elevation"]
    project.cod = pd.Timestamp(project_data["cod"])

    met_time_index_df = _read_snapshot_table(
        snapshot_name=snapshot_name,
        file_name="indeces_met_time_index.parquet",
    )

    valid_indices = None
    if simulation_start and simulation_end:
        tz = pytz.timezone(project.time_zone)
        start_dt = tz.localize(datetime.strptime(simulation_start, "%Y-%m-%d %H:%M:%S"))
        end_dt = tz.localize(datetime.strptime(simulation_end, "%Y-%m-%d %H:%M:%S"))

        met_time_index_df = met_time_index_df[
            (met_time_index_df["time"] >= start_dt)
            & (met_time_index_df["time"] <= end_dt)
        ]
        valid_indices = met_time_index_df.index

    indeces = Indeces(
        met_time_index=MetTimeIndex(met_time_index_df),
        string_index=SystemSeries(
            _extract_series(
                data_frame=_read_snapshot_table(
                    snapshot_name=snapshot_name,
                    file_name="indeces_string_index.parquet",
                ),
                column="string_id",
            )
        ),
        module_equipment_index=ModuleEquipmentSeries(
            _extract_series(
                data_frame=_read_snapshot_table(
                    snapshot_name=snapshot_name,
                    file_name="indeces_module_equipment_index.parquet",
                ),
                column="module_equipment_id",
            )
        ),
        racking_equipment_index=RackingEquipmentSeries(
            _extract_series(
                data_frame=_read_snapshot_table(
                    snapshot_name=snapshot_name,
                    file_name="indeces_racking_equipment_index.parquet",
                ),
                column="racking_equipment_id",
            )
        ),
        inverter_equipment_index=InverterEquipmentSeries(
            _extract_series(
                data_frame=_read_snapshot_table(
                    snapshot_name=snapshot_name,
                    file_name="indeces_inverter_equipment_index.parquet",
                ),
                column="pcs_equipment_id",
            )
        ),
        combiner_device_index=SystemSeries(
            _extract_series(
                data_frame=_read_snapshot_table(
                    snapshot_name=snapshot_name,
                    file_name="indeces_combiner_device_index.parquet",
                ),
                column="combiner_device_id",
            )
        ),
        inverter_device_index=InverterDeviceSeries(
            _extract_series(
                data_frame=_read_snapshot_table(
                    snapshot_name=snapshot_name,
                    file_name="indeces_inverter_device_index.parquet",
                ),
                column="pcs_device_id",
            )
        ),
        transformer_device_index=TransformerDeviceSeries(
            _extract_series(
                data_frame=_read_snapshot_table(
                    snapshot_name=snapshot_name,
                    file_name="indeces_transformer_device_index.parquet",
                ),
                column="transformer_device_id",
            )
        ),
    )

    quality_assurance_data = _read_snapshot_table(
        snapshot_name=snapshot_name,
        file_name="quality_assurance.parquet",
    )
    if valid_indices is not None:
        quality_assurance_data = quality_assurance_data.loc[valid_indices]

    quality_assurance = QualityAssurance(
        tier=MetTimeSeries(
            _extract_series(data_frame=quality_assurance_data, column="tier")
        ),
        tier_codes=MetTimeSeries(
            _extract_series(data_frame=quality_assurance_data, column="tier_codes")
        ),
    )

    met_data_table = _read_snapshot_table(
        snapshot_name=snapshot_name,
        file_name="met_data.parquet",
    )
    if valid_indices is not None:
        met_data_table = met_data_table.loc[valid_indices]

    met_data = MetDataObserved(met_data=met_data_table)

    simulation_config = SimulationConfig.initialize_with_overrides(
        **snapshot_metadata["simulation_config"]
    )

    system_data = _read_snapshot_table(
        snapshot_name=snapshot_name,
        file_name="system.parquet",
    )
    system = System(
        string_id=SystemSeries(
            _extract_series(data_frame=system_data, column="string_id")
        ),
        module_equipment_id=SystemSeries(
            _extract_series(data_frame=system_data, column="module_equipment_id")
        ),
        modules_per_string=SystemSeries(
            _extract_series(data_frame=system_data, column="modules_per_string")
        ),
        strings_per_combiner=SystemSeries(
            _extract_series(data_frame=system_data, column="strings_per_combiner")
        ),
        dc_line_to_combiner_stc=SystemSeries(
            _extract_series(data_frame=system_data, column="dc_line_to_combiner_stc")
        ),
        combiner_device_id=SystemSeries(
            _extract_series(data_frame=system_data, column="combiner_device_id")
        ),
        pitch=SystemSeries(pd.Series(dtype="float64")),
        racking_controls_gcr=SystemSeries(
            _extract_series(data_frame=system_data, column="racking_controls_gcr")
        ),
        racking_equipment_id=SystemSeries(
            _extract_series(data_frame=system_data, column="racking_equipment_id")
        ),
        racking_controls_algorithm=SystemSeries(pd.Series(dtype="object")),
        racking_device_id=SystemSeries(
            _extract_series(data_frame=system_data, column="racking_device_id")
        ),
        dc_line_to_inverter_stc=SystemSeries(
            _extract_series(data_frame=system_data, column="dc_line_to_inverter_stc")
        ),
        pcs_equipment_id=InverterDeviceSeries(
            _extract_series(data_frame=system_data, column="pcs_equipment_id")
        ),
        pcs_device_id=InverterDeviceSeries(
            _extract_series(data_frame=system_data, column="pcs_device_id")
        ),
        transformer_equipment_id=TransformerDeviceSeries(
            _extract_series(data_frame=system_data, column="transformer_equipment_id")
        ),
        transformer_device_id=TransformerDeviceSeries(
            _extract_series(data_frame=system_data, column="transformer_device_id")
        ),
        block_device_id=SystemSeries(
            _extract_series(data_frame=system_data, column="block_device_id")
        ),
        circuit_device_id=SystemSeries(
            _extract_series(data_frame=system_data, column="circuit_device_id")
        ),
        met_name=SystemSeries(
            _extract_series(data_frame=system_data, column="met_name")
        ),
    )

    module_data = _read_snapshot_table(
        snapshot_name=snapshot_name,
        file_name="modules.parquet",
    )
    modules = Module(
        module_equipment_id=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="module_equipment_id")
        ),
        company_id=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="company_id")
        ),
        manufacturer=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="manufacturer")
        ),
        model=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="model")
        ),
        family=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="family")
        ),
        technology=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="technology")
        ),
        bifaciality_factor=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="bifaciality_factor")
        ),
        pmax=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="pmax").rename(
                "module_p_max_stc"
            )
        ),
        isc=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="isc").rename(
                "module_i_sc_stc"
            )
        ),
        voc=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="voc").rename(
                "module_v_oc_stc"
            )
        ),
        imp=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="imp").rename(
                "module_i_mp_stc"
            )
        ),
        vmp=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="vmp").rename(
                "module_v_mp_stc"
            )
        ),
        efficiency=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="efficiency")
        ),
        gamma_pmax=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="gamma_pmax")
        ),
        alpha_isc=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="alpha_isc")
        ),
        beta_voc=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="beta_voc")
        ),
        warranted_degradation_rate=ModuleEquipmentSeries(
            _extract_series(
                data_frame=module_data,
                column="warranted_degradation_rate",
            )
        ),
        warranted_degradation_initial=ModuleEquipmentSeries(
            _extract_series(
                data_frame=module_data,
                column="warranted_degradation_initial",
            )
        ),
        length=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="length")
        ),
        width=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="width")
        ),
        area=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="area")
        ),
        frame_overhang=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="frame_overhang")
        ),
        has_ar_coating=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="has_ar_coating")
        ),
        half_cut=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="half_cut")
        ),
        cells_in_series=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="cells_in_series")
        ),
        photocurrent=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="photocurrent")
        ),
        diode_saturation_current=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="diode_saturation_current")
        ),
        r_series=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="r_series")
        ),
        r_shunt=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="r_shunt")
        ),
        r_shunt_0=ModuleEquipmentSeries(
            _extract_optional_series(data_frame=module_data, column="r_shunt_0")
        ),
        r_shunt_exponent=ModuleEquipmentSeries(
            _extract_optional_series(
                data_frame=module_data,
                column="r_shunt_exponent",
            )
        ),
        diode_ideality_factor=ModuleEquipmentSeries(
            _extract_optional_series(
                data_frame=module_data,
                column="diode_ideality_factor",
            )
        ),
        diode_ideality_factor_temp_coefficient=ModuleEquipmentSeries(
            _extract_optional_series(
                data_frame=module_data,
                column="diode_ideality_factor_temp_coefficient",
            )
        ),
        modified_ideality_factor=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="modified_ideality_factor")
        ),
        eg=ModuleEquipmentSeries(_extract_series(data_frame=module_data, column="eg")),
        degdt=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="degdt")
        ),
        data_source=ModuleEquipmentSeries(
            _extract_series(data_frame=module_data, column="data_source")
        ),
    )

    racking_data = _read_snapshot_table(
        snapshot_name=snapshot_name,
        file_name="rackings.parquet",
    )
    rackings = Racking(
        racking_equipment_id=RackingEquipmentSeries(
            _extract_series(data_frame=racking_data, column="racking_equipment_id")
        ),
        racking_type_id=RackingEquipmentSeries(
            _extract_series(data_frame=racking_data, column="racking_type_id")
        ),
        manufacturer=RackingEquipmentSeries(
            _extract_series(data_frame=racking_data, column="manufacturer")
        ),
        model=RackingEquipmentSeries(
            _extract_series(data_frame=racking_data, column="model")
        ),
        max_rotation_angle=RackingEquipmentSeries(
            _extract_series(data_frame=racking_data, column="max_rotation_angle")
        ),
        min_rotation_angle=RackingEquipmentSeries(
            _extract_series(data_frame=racking_data, column="min_rotation_angle")
        ),
        pile_height=RackingEquipmentSeries(
            _extract_series(data_frame=racking_data, column="pile_height")
        ),
        structure_shading_factor=RackingEquipmentSeries(
            _extract_series(data_frame=racking_data, column="structure_shading_factor")
        ),
        rear_mismatch_factor=RackingEquipmentSeries(
            _extract_series(data_frame=racking_data, column="rear_mismatch_factor")
        ),
    )

    inverter_data = _read_snapshot_table(
        snapshot_name=snapshot_name,
        file_name="inverters.parquet",
    )
    for array_column in [
        "power_max_at_reference_temp",
        "reference_temp",
        "voltage_nominal_efficiency",
        "efficiency_at_low_voltage",
        "efficiency_at_mid_voltage",
        "efficiency_at_high_voltage",
    ]:
        inverter_data.loc[:, array_column] = inverter_data.loc[:, array_column].map(
            lambda value: _map_to_numpy_array(value=value)
        )

    inverters = Inverter(
        pcs_equipment_id=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="pcs_equipment_id")
        ),
        manufacturer=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="manufacturer")
        ),
        model=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="model")
        ),
        voltage_mpp_min=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="voltage_mpp_min")
        ),
        voltage_mpp_max=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="voltage_mpp_max")
        ),
        voltage_start_up=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="voltage_start_up")
        ),
        voltage_min=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="voltage_min")
        ),
        voltage_max=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="voltage_max")
        ),
        current_max=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="current_max")
        ),
        power_max_at_reference_temp=InverterEquipmentSeries(
            _extract_series(
                data_frame=inverter_data,
                column="power_max_at_reference_temp",
            )
        ),
        reference_temp=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="reference_temp")
        ),
        voltage_nominal_efficiency=InverterEquipmentSeries(
            _extract_series(
                data_frame=inverter_data,
                column="voltage_nominal_efficiency",
            )
        ),
        efficiency_at_low_voltage=InverterEquipmentSeries(
            _extract_series(
                data_frame=inverter_data, column="efficiency_at_low_voltage"
            )
        ),
        efficiency_at_mid_voltage=InverterEquipmentSeries(
            _extract_series(
                data_frame=inverter_data, column="efficiency_at_mid_voltage"
            )
        ),
        efficiency_at_high_voltage=InverterEquipmentSeries(
            _extract_series(
                data_frame=inverter_data, column="efficiency_at_high_voltage"
            )
        ),
        power_start_up=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="power_start_up")
        ),
        power_ac_nominal=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="power_ac_nominal")
        ),
        power_dc_nominal=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="power_dc_nominal")
        ),
        voltage_dc_nominal=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="voltage_dc_nominal")
        ),
        c0=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="c0")
        ),
        c1=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="c1")
        ),
        c2=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="c2")
        ),
        c3=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="c3")
        ),
        night_tare=InverterEquipmentSeries(
            _extract_series(data_frame=inverter_data, column="night_tare")
        ),
    )

    return SimulationInputs(
        version=snapshot_metadata["version"],
        project=project,
        indeces=indeces,
        quality_assurance=quality_assurance,
        met_data=met_data,
        simulation_config=simulation_config,
        system=system,
        modules=modules,
        rackings=rackings,
        inverters=inverters,
        axis_azimuth=snapshot_metadata["axis_azimuth"],
        engine=sqlalchemy.create_engine("sqlite+pysqlite:///:memory:"),
        SIMULATION_TEMPORAL_MODE=SimulationTemporalMode(
            snapshot_metadata["SIMULATION_TEMPORAL_MODE"]
        ),
        ENVIRONMENT=snapshot_metadata["ENVIRONMENT"],
    )


def install_snapshot_inputs_loader_patch(
    *, monkeypatch: Any, snapshot_name: str
) -> None:
    # Store the original method so we can call it to capture data if needed
    original_from_proximal_db = SimulationInputs.from_proximal_db

    async def snapshot_loader(
        cls,
        *,
        project_name_short: str,
        simulation_temporal_mode: SimulationTemporalMode,
        simulation_start: str | None = None,
        simulation_end: str | None = None,
        **config_overrides: Any,
    ) -> SimulationInputs:
        # CAPTURE MODE: If snapshot is missing or incomplete, fetch from DB and save.
        if not _is_snapshot_complete(snapshot_name=snapshot_name):
            logger.info("Snapshot '%s' not found. Capturing from DB...", snapshot_name)
            simulation_inputs = await original_from_proximal_db(
                project_name_short=project_name_short,
                simulation_temporal_mode=simulation_temporal_mode,
                simulation_start=simulation_start,
                simulation_end=simulation_end,
                **config_overrides,
            )
            _raise_for_incompatible_pvsyst_snapshot(simulation_inputs=simulation_inputs)
            save_snapshot_inputs(
                snapshot_name=snapshot_name, simulation_inputs=simulation_inputs
            )
            return simulation_inputs

        # LOAD MODE: Read from existing snapshot
        simulation_inputs = read_snapshot_inputs(
            snapshot_name=snapshot_name,
            simulation_start=simulation_start,
            simulation_end=simulation_end,
        )
        simulation_inputs.SIMULATION_TEMPORAL_MODE = simulation_temporal_mode

        for key, value in config_overrides.items():
            if hasattr(simulation_inputs.simulation_config, key):
                setattr(simulation_inputs.simulation_config, key, value)

        _raise_for_incompatible_pvsyst_snapshot(simulation_inputs=simulation_inputs)

        return simulation_inputs

    monkeypatch.setattr(
        SimulationInputs,
        "from_proximal_db",
        classmethod(snapshot_loader),
    )


def build_output_file_path(
    *,
    test_namespace: str,
    project_name_short: str,
    simulation_start: str,
    simulation_level: SimulationLevel,
) -> Path:
    simulation_datetime = datetime.strptime(simulation_start, "%Y-%m-%d %H:%M:%S")
    date_part = simulation_datetime.strftime("%Y_%m_%d")
    time_part = simulation_datetime.strftime("%H_%M_%S")

    return (
        _artifacts_root()
        / test_namespace
        / project_name_short
        / date_part
        / f"_{simulation_level}_{time_part}.pq"
    )


def remove_output_file_if_exists(*, output_file_path: Path) -> None:
    if output_file_path.exists():
        output_file_path.unlink()


def remove_output_files_if_exist(
    *,
    test_namespace: str,
    project_name_short: str,
    simulation_start: str,
    simulation_levels: Iterable[SimulationLevel],
) -> None:
    for simulation_level in simulation_levels:
        remove_output_file_if_exists(
            output_file_path=build_output_file_path(
                test_namespace=test_namespace,
                project_name_short=project_name_short,
                simulation_start=simulation_start,
                simulation_level=simulation_level,
            )
        )


def install_unique_export_patch(
    *,
    monkeypatch: Any,
    test_namespace: str,
    static_output_files: dict[SimulationLevel, Path] | None = None,
) -> None:
    def export_to_unique_file(
        *,
        results: pd.DataFrame,
        simulation_level: SimulationLevel,
        project_name_short: str,
        simulation_start: str | None,
        ENVIRONMENT: str,
    ) -> None:
        _ = ENVIRONMENT
        if simulation_start is None:
            raise ValueError("simulation_start cannot be None for snapshot tests")

        output_file_path = build_output_file_path(
            test_namespace=test_namespace,
            project_name_short=project_name_short,
            simulation_start=simulation_start,
            simulation_level=simulation_level,
        )
        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        if static_output_files and simulation_level in static_output_files:
            pd.read_parquet(static_output_files[simulation_level]).to_parquet(
                output_file_path,
                index=False,
            )
            return

        results.to_parquet(output_file_path, index=False)

    monkeypatch.setattr(c_export, "export_to_file", export_to_unique_file)
