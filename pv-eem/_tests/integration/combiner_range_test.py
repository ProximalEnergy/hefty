import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import p03_export.c_export as c_export
import pandas as pd
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
from p01_get_data.class_simulation_inputs import SimulationInputs
from p01_get_data.s00_get_simulation_config import SimulationConfig
from p01_get_data.source_proximal.s03_get_project import Project
from p01_get_data.source_proximal.s04_get_system_data import System
from p01_get_data.source_proximal.s09_get_inverter_data import Inverter
from p01_get_data.source_proximal.s09_get_module_data import Module
from p01_get_data.source_proximal.s09_get_racking_data import Racking
from p03_export.s00_simulation_level import SimulationLevel
from src.main import get_expected_energy
from src.p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from src.p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
from src.p02_simulation.p3_epoai.s05_soiling import ModelSoiling
from src.p02_simulation.p4_dc_iv.s02_single_diode_params import ModelSingleDiode

SNAPSHOT_NAME = Path(__file__).stem
SNAPSHOT_RELATIVE_DIR = f"_tests/_artifacts/snapshots/{SNAPSHOT_NAME}"
TEST_NAME = "test_simulation"
OUTPUT_NAMESPACE = f"{SNAPSHOT_NAME}_{TEST_NAME}"
PROJECT_NAME_SHORT = "double_black_diamond"
SIMULATION_START = "2024-10-20 00:00:00"
SIMULATION_END = "2024-10-20 23:59:59"
SIMULATION_LEVEL = SimulationLevel.COMBINER
_SIMULATION_DATETIME = datetime.strptime(SIMULATION_START, "%Y-%m-%d %H:%M:%S")
_OUTPUT_DATE_PART = _SIMULATION_DATETIME.strftime("%Y_%m_%d")
_OUTPUT_TIME_PART = _SIMULATION_DATETIME.strftime("%H_%M_%S")
OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "_artifacts"
    / OUTPUT_NAMESPACE
    / PROJECT_NAME_SHORT
    / _OUTPUT_DATE_PART
)
OUTPUT_FILE_PATH = OUTPUT_DIR / f"_{SIMULATION_LEVEL}_{_OUTPUT_TIME_PART}.pq"
PVSYST_REQUIRED_MODULE_COLUMNS = (
    "r_shunt_0",
    "r_shunt_exponent",
    "diode_ideality_factor",
    "diode_ideality_factor_temp_coefficient",
)
PVSYST_SNAPSHOT_ERROR = (
    "Snapshot incompatible with PVSyst, check database and recapture"
)


def _snapshot_dir() -> Path:
    return (
        Path(__file__).resolve().parents[1] / "_artifacts" / "snapshots" / SNAPSHOT_NAME
    )


def _snapshot_metadata_path() -> Path:
    return _snapshot_dir() / "metadata.json"


def _snapshot_table_path(*, file_name: str) -> Path:
    return _snapshot_dir() / file_name


def _read_snapshot_metadata() -> dict[str, Any]:
    metadata_path = _snapshot_metadata_path()
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Missing snapshot metadata at {SNAPSHOT_RELATIVE_DIR}/metadata.json. "
            "Generate this file once before running this test."
        )

    with metadata_path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def _read_snapshot_table(*, file_name: str) -> pd.DataFrame:
    table_path = _snapshot_table_path(file_name=file_name)
    if not table_path.exists():
        raise FileNotFoundError(
            f"Missing snapshot table at {SNAPSHOT_RELATIVE_DIR}/{file_name}. "
            "Generate this file once before running this test."
        )
    return pd.read_parquet(table_path)


def _to_series(*, data_frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in data_frame:
        raise KeyError(f"Missing column '{column}' in snapshot table.")
    return data_frame.loc[:, column]


def _to_optional_series(*, data_frame: pd.DataFrame, column: str) -> pd.Series:
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


def _to_numpy_array(value: Any) -> Any:
    if isinstance(value, list):
        return np.array(value)
    return value


def _read_inputs_snapshot() -> SimulationInputs:
    snapshot_metadata = _read_snapshot_metadata()

    project_data = snapshot_metadata["project"]
    project = object.__new__(Project)
    project.name_short = project_data["name_short"]
    project.name_long = project_data["name_long"]
    project.data_table = project_data["data_table"]
    project.time_zone = project_data["time_zone"]
    project.poi_limit = project_data["poi_limit"]
    project.longitude = project_data["longitude"]
    project.latitude = project_data["latitude"]
    project.elevation = project_data["elevation"]
    project.cod = pd.Timestamp(project_data["cod"])

    met_time_index_df = _read_snapshot_table(file_name="indeces_met_time_index.parquet")
    indeces = Indeces(
        met_time_index=MetTimeIndex(met_time_index_df),
        string_index=SystemSeries(
            _to_series(
                data_frame=_read_snapshot_table(
                    file_name="indeces_string_index.parquet"
                ),
                column="string_id",
            )
        ),
        module_equipment_index=ModuleEquipmentSeries(
            _to_series(
                data_frame=_read_snapshot_table(
                    file_name="indeces_module_equipment_index.parquet"
                ),
                column="module_equipment_id",
            )
        ),
        racking_equipment_index=RackingEquipmentSeries(
            _to_series(
                data_frame=_read_snapshot_table(
                    file_name="indeces_racking_equipment_index.parquet"
                ),
                column="racking_equipment_id",
            )
        ),
        inverter_equipment_index=InverterEquipmentSeries(
            _to_series(
                data_frame=_read_snapshot_table(
                    file_name="indeces_inverter_equipment_index.parquet"
                ),
                column="pcs_equipment_id",
            )
        ),
        combiner_device_index=SystemSeries(
            _to_series(
                data_frame=_read_snapshot_table(
                    file_name="indeces_combiner_device_index.parquet"
                ),
                column="combiner_device_id",
            )
        ),
        inverter_device_index=InverterDeviceSeries(
            _to_series(
                data_frame=_read_snapshot_table(
                    file_name="indeces_inverter_device_index.parquet"
                ),
                column="pcs_device_id",
            )
        ),
        transformer_device_index=TransformerDeviceSeries(
            _to_series(
                data_frame=_read_snapshot_table(
                    file_name="indeces_transformer_device_index.parquet"
                ),
                column="transformer_device_id",
            )
        ),
    )

    quality_assurance_data = _read_snapshot_table(file_name="quality_assurance.parquet")
    quality_assurance = QualityAssurance(
        tier=MetTimeSeries(
            _to_series(data_frame=quality_assurance_data, column="tier")
        ),
        tier_codes=MetTimeSeries(
            _to_series(data_frame=quality_assurance_data, column="tier_codes")
        ),
    )

    met_data = MetDataObserved(
        met_data=_read_snapshot_table(file_name="met_data.parquet")
    )

    simulation_config = SimulationConfig.initialize_with_overrides(
        **snapshot_metadata["simulation_config"]
    )

    system_data = _read_snapshot_table(file_name="system.parquet")
    system = System(
        string_id=SystemSeries(_to_series(data_frame=system_data, column="string_id")),
        module_equipment_id=SystemSeries(
            _to_series(data_frame=system_data, column="module_equipment_id")
        ),
        modules_per_string=SystemSeries(
            _to_series(data_frame=system_data, column="modules_per_string")
        ),
        strings_per_combiner=SystemSeries(
            _to_series(data_frame=system_data, column="strings_per_combiner")
        ),
        dc_line_to_combiner_stc=SystemSeries(
            _to_series(data_frame=system_data, column="dc_line_to_combiner_stc")
        ),
        combiner_device_id=SystemSeries(
            _to_series(data_frame=system_data, column="combiner_device_id")
        ),
        pitch=SystemSeries(pd.Series(dtype="float64")),
        racking_controls_gcr=SystemSeries(
            _to_series(data_frame=system_data, column="racking_controls_gcr")
        ),
        racking_equipment_id=SystemSeries(
            _to_series(data_frame=system_data, column="racking_equipment_id")
        ),
        racking_controls_algorithm=SystemSeries(pd.Series(dtype="object")),
        racking_device_id=SystemSeries(
            _to_series(data_frame=system_data, column="racking_device_id")
        ),
        dc_line_to_inverter_stc=SystemSeries(
            _to_series(data_frame=system_data, column="dc_line_to_inverter_stc")
        ),
        pcs_equipment_id=InverterDeviceSeries(
            _to_series(data_frame=system_data, column="pcs_equipment_id")
        ),
        pcs_device_id=InverterDeviceSeries(
            _to_series(data_frame=system_data, column="pcs_device_id")
        ),
        transformer_equipment_id=TransformerDeviceSeries(
            _to_series(data_frame=system_data, column="transformer_equipment_id")
        ),
        transformer_device_id=TransformerDeviceSeries(
            _to_series(data_frame=system_data, column="transformer_device_id")
        ),
        block_device_id=SystemSeries(
            _to_series(data_frame=system_data, column="block_device_id")
        ),
        circuit_device_id=SystemSeries(
            _to_series(data_frame=system_data, column="circuit_device_id")
        ),
        met_name=SystemSeries(_to_series(data_frame=system_data, column="met_name")),
    )

    module_data = _read_snapshot_table(file_name="modules.parquet")
    modules = Module(
        module_equipment_id=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="module_equipment_id")
        ),
        company_id=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="company_id")
        ),
        manufacturer=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="manufacturer")
        ),
        model=ModuleEquipmentSeries(_to_series(data_frame=module_data, column="model")),
        family=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="family")
        ),
        technology=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="technology")
        ),
        bifaciality_factor=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="bifaciality_factor")
        ),
        pmax=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="pmax").rename("module_p_max_stc")
        ),
        isc=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="isc").rename("module_i_sc_stc")
        ),
        voc=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="voc").rename("module_v_oc_stc")
        ),
        imp=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="imp").rename("module_i_mp_stc")
        ),
        vmp=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="vmp").rename("module_v_mp_stc")
        ),
        efficiency=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="efficiency")
        ),
        gamma_pmax=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="gamma_pmax")
        ),
        alpha_isc=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="alpha_isc")
        ),
        beta_voc=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="beta_voc")
        ),
        warranted_degradation_rate=ModuleEquipmentSeries(
            _to_series(
                data_frame=module_data,
                column="warranted_degradation_rate",
            )
        ),
        warranted_degradation_initial=ModuleEquipmentSeries(
            _to_series(
                data_frame=module_data,
                column="warranted_degradation_initial",
            )
        ),
        length=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="length")
        ),
        width=ModuleEquipmentSeries(_to_series(data_frame=module_data, column="width")),
        area=ModuleEquipmentSeries(_to_series(data_frame=module_data, column="area")),
        frame_overhang=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="frame_overhang")
        ),
        has_ar_coating=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="has_ar_coating")
        ),
        half_cut=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="half_cut")
        ),
        cells_in_series=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="cells_in_series")
        ),
        photocurrent=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="photocurrent")
        ),
        diode_saturation_current=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="diode_saturation_current")
        ),
        r_series=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="r_series")
        ),
        r_shunt=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="r_shunt")
        ),
        r_shunt_0=ModuleEquipmentSeries(
            _to_optional_series(data_frame=module_data, column="r_shunt_0")
        ),
        r_shunt_exponent=ModuleEquipmentSeries(
            _to_optional_series(
                data_frame=module_data,
                column="r_shunt_exponent",
            )
        ),
        diode_ideality_factor=ModuleEquipmentSeries(
            _to_optional_series(
                data_frame=module_data,
                column="diode_ideality_factor",
            )
        ),
        diode_ideality_factor_temp_coefficient=ModuleEquipmentSeries(
            _to_optional_series(
                data_frame=module_data,
                column="diode_ideality_factor_temp_coefficient",
            )
        ),
        modified_ideality_factor=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="modified_ideality_factor")
        ),
        eg=ModuleEquipmentSeries(_to_series(data_frame=module_data, column="eg")),
        degdt=ModuleEquipmentSeries(_to_series(data_frame=module_data, column="degdt")),
        data_source=ModuleEquipmentSeries(
            _to_series(data_frame=module_data, column="data_source")
        ),
    )

    racking_data = _read_snapshot_table(file_name="rackings.parquet")
    rackings = Racking(
        racking_equipment_id=RackingEquipmentSeries(
            _to_series(data_frame=racking_data, column="racking_equipment_id")
        ),
        racking_type_id=RackingEquipmentSeries(
            _to_series(data_frame=racking_data, column="racking_type_id")
        ),
        manufacturer=RackingEquipmentSeries(
            _to_series(data_frame=racking_data, column="manufacturer")
        ),
        model=RackingEquipmentSeries(
            _to_series(data_frame=racking_data, column="model")
        ),
        max_rotation_angle=RackingEquipmentSeries(
            _to_series(data_frame=racking_data, column="max_rotation_angle")
        ),
        min_rotation_angle=RackingEquipmentSeries(
            _to_series(data_frame=racking_data, column="min_rotation_angle")
        ),
        pile_height=RackingEquipmentSeries(
            _to_series(data_frame=racking_data, column="pile_height")
        ),
        structure_shading_factor=RackingEquipmentSeries(
            _to_series(data_frame=racking_data, column="structure_shading_factor")
        ),
        rear_mismatch_factor=RackingEquipmentSeries(
            _to_series(data_frame=racking_data, column="rear_mismatch_factor")
        ),
    )

    inverter_data = _read_snapshot_table(file_name="inverters.parquet")
    for array_column in [
        "power_max_at_reference_temp",
        "reference_temp",
        "voltage_nominal_efficiency",
        "efficiency_at_low_voltage",
        "efficiency_at_mid_voltage",
        "efficiency_at_high_voltage",
    ]:
        inverter_data.loc[:, array_column] = inverter_data.loc[:, array_column].map(
            _to_numpy_array
        )
    inverters = Inverter(
        pcs_equipment_id=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="pcs_equipment_id")
        ),
        manufacturer=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="manufacturer")
        ),
        model=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="model")
        ),
        voltage_mpp_min=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="voltage_mpp_min")
        ),
        voltage_mpp_max=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="voltage_mpp_max")
        ),
        voltage_start_up=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="voltage_start_up")
        ),
        voltage_min=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="voltage_min")
        ),
        voltage_max=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="voltage_max")
        ),
        current_max=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="current_max")
        ),
        power_max_at_reference_temp=InverterEquipmentSeries(
            _to_series(
                data_frame=inverter_data,
                column="power_max_at_reference_temp",
            )
        ),
        reference_temp=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="reference_temp")
        ),
        voltage_nominal_efficiency=InverterEquipmentSeries(
            _to_series(
                data_frame=inverter_data,
                column="voltage_nominal_efficiency",
            )
        ),
        efficiency_at_low_voltage=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="efficiency_at_low_voltage")
        ),
        efficiency_at_mid_voltage=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="efficiency_at_mid_voltage")
        ),
        efficiency_at_high_voltage=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="efficiency_at_high_voltage")
        ),
        power_start_up=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="power_start_up")
        ),
        power_ac_nominal=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="power_ac_nominal")
        ),
        power_dc_nominal=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="power_dc_nominal")
        ),
        voltage_dc_nominal=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="voltage_dc_nominal")
        ),
        c0=InverterEquipmentSeries(_to_series(data_frame=inverter_data, column="c0")),
        c1=InverterEquipmentSeries(_to_series(data_frame=inverter_data, column="c1")),
        c2=InverterEquipmentSeries(_to_series(data_frame=inverter_data, column="c2")),
        c3=InverterEquipmentSeries(_to_series(data_frame=inverter_data, column="c3")),
        night_tare=InverterEquipmentSeries(
            _to_series(data_frame=inverter_data, column="night_tare")
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


def _install_inputs_loader_patch(*, monkeypatch: Any) -> None:
    async def snapshot_loader(
        cls,
        *,
        project_name_short: str,
        simulation_temporal_mode: SimulationTemporalMode,
        simulation_start: str | None = None,
        simulation_end: str | None = None,
        **config_overrides: Any,
    ) -> SimulationInputs:
        _ = cls
        _ = project_name_short
        _ = simulation_start
        _ = simulation_end
        simulation_inputs = _read_inputs_snapshot()
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


def _install_unique_export_patch(*, monkeypatch: Any) -> None:
    def export_to_unique_file(
        *,
        results: pd.DataFrame,
        simulation_level: SimulationLevel,
        project_name_short: str,
        simulation_start: str | None,
        ENVIRONMENT: str,
    ) -> None:
        _ = ENVIRONMENT
        if project_name_short != PROJECT_NAME_SHORT:
            raise ValueError(
                "Unexpected project_name_short: "
                f"{project_name_short}. Expected {PROJECT_NAME_SHORT}."
            )
        if simulation_start != SIMULATION_START:
            raise ValueError(
                "Unexpected simulation_start: "
                f"{simulation_start}. Expected {SIMULATION_START}."
            )
        if simulation_level != SIMULATION_LEVEL:
            return
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        results.to_parquet(OUTPUT_FILE_PATH, index=False)

    monkeypatch.setattr(c_export, "export_to_file", export_to_unique_file)


def test_simulation(monkeypatch):
    os.environ["ENVIRONMENT"] = "DEV"
    _install_inputs_loader_patch(monkeypatch=monkeypatch)
    _install_unique_export_patch(monkeypatch=monkeypatch)

    # --- File Load ---
    if OUTPUT_FILE_PATH.exists():
        OUTPUT_FILE_PATH.unlink()

    # --- Main Simulation ---
    _results: dict = asyncio.run(
        get_expected_energy(
            # ARGS
            project_name_short=PROJECT_NAME_SHORT,
            simulation_temporal_mode=SimulationTemporalMode.WINDOW,
            simulation_start=SIMULATION_START,
            simulation_end=SIMULATION_END,
            # KWARGS
            sun_position_offset=0,
            soiling=ModelSoiling.NONE,
            circumsolar=ModelCircumsolar.DIFFUSE,
            single_diode_model=ModelSingleDiode.DESOTO,
        )
    )
    assert _results.get("status_code") == 200, _results
    combiners = pd.read_parquet(OUTPUT_FILE_PATH)

    # --- Test ---
    assert combiners["p_mp"].max() < 400_000, (
        f"Maximum p_mp value {combiners['p_mp'].max()} exceeds 400,000"
    )

    assert combiners["p_mp"].min() >= 0, (
        f"Minimum p_mp value {combiners['p_mp'].min()} is less than 0"
    )
