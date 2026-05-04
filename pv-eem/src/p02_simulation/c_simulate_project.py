import logging
from collections.abc import Generator

from interfaces import Indeces, QualityAssurance
from p01_get_data.class_simulation_inputs import MetDataObserved, SimulationInputs
from p01_get_data.s00_get_simulation_config import SimulationConfig
from p01_get_data.source_proximal.s03_get_project import PvEemProject
from p01_get_data.source_proximal.s04_get_system_data import System
from p01_get_data.source_proximal.s09_get_inverter_data import PvEemInverter
from p01_get_data.source_proximal.s09_get_module_data import Module
from p01_get_data.source_proximal.s09_get_racking_data import PvEemRacking
from p02_simulation.p0_meteorological.c_meteorological import MetDataComputed
from p02_simulation.p1_rotations.c_rotation_angles import RotationAngles
from p02_simulation.p2_poai.c_poai import PlaneOfArrayIrradiance
from p02_simulation.p3_epoai.c_epoai import EffectivePlaneOfArrayIrradiance
from p02_simulation.p4_dc_iv.c_dc_iv import PowerAtCombiner
from p02_simulation.p5_inverter.c_inverter import InverterPower
from p02_simulation.p6_transformer.c_transformer import TransformerPower
from p02_simulation.p8_poi.c_poi import ProjectPower


def simulate_project(
    *,
    inputs: SimulationInputs,
) -> Generator[
    PlaneOfArrayIrradiance
    | PowerAtCombiner
    | InverterPower
    | TransformerPower
    | ProjectPower,
    None,
    None,
]:
    # --- HARDCODED ---
    """Run simulate_project."""
    ALBEDO = 0.2  # ratio

    # --- Break Apart Inputs ---
    project: PvEemProject = inputs.project
    simulation_config: SimulationConfig = inputs.simulation_config
    indeces: Indeces = inputs.indeces
    quality_assurance: QualityAssurance = inputs.quality_assurance
    met_data_observed: MetDataObserved = inputs.met_data
    system: System = inputs.system
    modules: Module = inputs.modules
    rackings: PvEemRacking = inputs.rackings
    inverters: PvEemInverter = inputs.inverters

    version: str = inputs.version
    AXIS_AZIMUTH: float = inputs.axis_azimuth

    # --- Logging ---
    logging.info(f"... Begin simulation with v{version}")

    # --- Phase 0:  Calculate MetDataComputed Parameters ---
    met_data_computed: MetDataComputed = MetDataComputed(
        latitude=project.latitude,
        longitude=project.longitude,
        elevation=project.elevation,
        indeces=indeces,
        met_data_observed=met_data_observed,
        simulation_config=simulation_config,
    )
    # met_data_computed.to_timeseries_csv(indeces=indeces)

    # --- Phase 1:  Calculate Rotation Angles ---
    rotations = RotationAngles(
        indeces=indeces,
        system=system,
        module_technology=modules.technology,
        max_rotation_angle=rackings.max_rotation_angle,
        solar_apparent_zenith=met_data_computed.solar_apparent_zenith,
        solar_azimuth=met_data_computed.solar_azimuth,
        module_length=modules.length,
        AXIS_AZIMUTH=AXIS_AZIMUTH,
    )

    # --- Phase 2:  Calculate Plane of Array Irradiance (POAI) ---
    poai = PlaneOfArrayIrradiance(
        simulation_config=simulation_config,
        indeces=indeces,
        quality_assurance=quality_assurance,
        surface_tilt=rotations.surface_tilt,
        surface_azimuth=rotations.surface_azimuth,
        aoi=rotations.aoi,
        ghi=met_data_observed.ghi,
        poa=met_data_observed.poa,
        site_pressure=met_data_computed.site_pressure,
        solar_azimuth=met_data_computed.solar_azimuth,
        solar_zenith=met_data_computed.solar_zenith,
        solar_apparent_zenith=met_data_computed.solar_apparent_zenith,
        dni=met_data_computed.dni,
        dhi=met_data_computed.dhi,
        dni_extra=met_data_computed.dni_extra,
        temp_dew=met_data_computed.temp_dew,
        air_mass_relative=met_data_computed.air_mass_relative,
        combiner_ids_by_string=system.combiner_device_id,
        racking_ids_by_string=system.racking_equipment_id,
        racking_controls_gcr=system.racking_controls_gcr,
        racking_height=rackings.pile_height,
        module_ids_by_string=system.module_equipment_id,
        pitch=system.pitch,
        module_bifaciality_factor=modules.bifaciality_factor,
        ALBEDO=ALBEDO,
        AXIS_AZIMUTH=AXIS_AZIMUTH,
    )
    # poai.to_poai_csv(target_string_id=0)
    logging.info("...POAI step complete")
    yield poai

    # --- Phase 4:  Calculate Effective Plane of Array Irradiance (EPOAI) ---
    epoai = EffectivePlaneOfArrayIrradiance(
        simulation_config=simulation_config,
        indeces=indeces,
        poai=poai,
        soil_percent=met_data_observed.soil_percent,
        apparent_zenith=met_data_computed.solar_apparent_zenith,
        azimuth=met_data_computed.solar_azimuth,
        air_mass_absolute=met_data_computed.air_mass_absolute,
        precipitable_water=met_data_computed.precipitable_water,
        pitch=system.pitch,
        racking_controls_gcr=system.racking_controls_gcr,
        module_id_by_string=system.module_equipment_id,
        racking_id_by_string=system.racking_equipment_id,
        tracker_theta=rotations.tracker_theta,
        surface_tilt=rotations.surface_tilt,
        aoi=rotations.aoi,
        module_length=modules.length,
        module_technology=modules.technology,
        module_is_half_cut=modules.half_cut,
        module_has_ar_coating=modules.has_ar_coating,
        module_bifaciality_factor=modules.bifaciality_factor,
        racking_rear_mismatch_factor=rackings.rear_mismatch_factor,
        racking_structure_shade_factor=rackings.structure_shading_factor,
        AXIS_AZIMUTH=AXIS_AZIMUTH,
    )
    # epoai.to_epoai_csv(indeces=indeces)
    logging.info("... EPOAI step complete")

    # --- Phase 5:  Calculate DC Current and Voltage (DC IV) ---
    power_at_combiner = PowerAtCombiner(
        single_diode_model=simulation_config.single_diode_model,
        degradation_model=simulation_config.degradation,
        dc_wiring_to_combiner_model=simulation_config.dc_wiring_to_combiner,
        indeces=indeces,
        quality_assurance=quality_assurance,
        egpoai=epoai.gpoai,
        cod=project.cod,
        module_id_by_string=system.module_equipment_id,
        modules=modules,
        temperature_ambient=met_data_observed.ambient_temperature,
        combiner_device_id=system.combiner_device_id,
        modules_per_string=system.modules_per_string,
        strings_per_combiner=system.strings_per_combiner,
        dc_line_to_combiner_stc=system.dc_line_to_combiner_stc,
        dc_line_to_inverter_stc=system.dc_line_to_inverter_stc,
    )

    logging.info("...Combiner step complete")
    yield power_at_combiner

    # --- INVERTER STEP ---
    power_at_inverter = InverterPower(
        simulation_config=simulation_config,
        indeces=indeces,
        power_at_combiner=power_at_combiner,
        inverters=inverters,
        inverter_device_ids=system.pcs_device_id,
        inverter_equipment_ids=system.pcs_equipment_id,
    )
    logging.info("...Inverter step complete")
    yield power_at_inverter

    # --- TRANSFORMER STEP ---
    power_at_transformer = TransformerPower(
        indeces=indeces,
        power_at_inverter=power_at_inverter,
        inverters=inverters,
        transformer_device_ids=system.transformer_device_id,
        transformer_equipment_ids=system.transformer_equipment_id,
    )
    logging.info("...Transformer step complete")
    yield power_at_transformer

    # --- POI STEP ---
    poi = ProjectPower(
        indeces=indeces,
        power_at_transformer=power_at_transformer,
        poi_limit=project.poi_limit,
    )
    logging.info("...POI step complete")
    yield poi
