from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd
from interfaces import (
    Indeces,
    MetTimeSeries,
    ModuleEquipmentSeries,
    QualityAssurance,
    RackingEquipmentSeries,
    StringMetTimeSeries,
    SystemSeries,
    TimeSeries,
)
from p02_simulation.p2_poai.s00_retro_transposition import HorizontalIrradianceRetro
from p02_simulation.p2_poai.s01_select_components import HorizontalIrradiance
from p02_simulation.p2_poai.s02_sky_diffuse import SkyDiffuse
from p02_simulation.p2_poai.s03_ground_diffuse import GroundDiffuse
from p02_simulation.p2_poai.s04_beam import Beam
from p02_simulation.p2_poai.s05_rear_poa import RearPlaneOfArrayIrradiance

if TYPE_CHECKING:
    from p01_get_data.s00_get_simulation_config import SimulationConfig


@dataclass(init=False, slots=True)
class PlaneOfArrayIrradiance:
    """PlaneOfArrayIrradiance."""

    time: StringMetTimeSeries
    string_ids: StringMetTimeSeries
    device_ids: StringMetTimeSeries
    tier: MetTimeSeries
    tier_codes: MetTimeSeries

    gpoai: StringMetTimeSeries
    isotropic: StringMetTimeSeries
    circumsolar: StringMetTimeSeries
    horizon: StringMetTimeSeries
    beam: StringMetTimeSeries
    ground_diffuse: StringMetTimeSeries
    rear: StringMetTimeSeries

    def __init__(
        self,
        *,
        simulation_config: SimulationConfig,
        indeces: Indeces,
        quality_assurance: QualityAssurance,
        surface_tilt: StringMetTimeSeries,
        surface_azimuth: StringMetTimeSeries,
        aoi: StringMetTimeSeries,
        ghi: MetTimeSeries,
        dni: MetTimeSeries,
        dni_extra: TimeSeries,
        dhi: MetTimeSeries,
        poa: MetTimeSeries,
        temp_dew: MetTimeSeries,
        solar_azimuth: TimeSeries,
        solar_zenith: TimeSeries,
        solar_apparent_zenith: TimeSeries,
        site_pressure: float,
        air_mass_relative: TimeSeries,
        pitch: SystemSeries,
        combiner_ids_by_string: SystemSeries,
        racking_ids_by_string: SystemSeries,
        module_ids_by_string: SystemSeries,
        racking_controls_gcr: SystemSeries,
        racking_height: RackingEquipmentSeries,
        module_bifaciality_factor: ModuleEquipmentSeries,
        ALBEDO: float,
        AXIS_AZIMUTH: float,
    ):
        """Calculate the Plane of Array Irradiance (POAI) and its components"""
        horizontal_irradiance_retro = HorizontalIrradianceRetro(
            model=simulation_config.retro_transposition,
            indeces=indeces,
            surface_tilt=surface_tilt,
            surface_azimuth=surface_azimuth,
            aoi=aoi,
            poa=poa,
            solar_azimuth=solar_azimuth,
            solar_zenith=solar_zenith,
            temp_dew=temp_dew,
            site_pressure=site_pressure,
            ALBEDO=ALBEDO,
        )

        horizontal_irradiance = HorizontalIrradiance(
            indeces=indeces,
            quality_assurance=quality_assurance,
            horizontal_irradiance_retro=horizontal_irradiance_retro,
            ghi=ghi,
            dni=dni,
            dhi=dhi,
            use_poa_only=simulation_config.use_poa_only,
        )

        sky_diffuse = SkyDiffuse(
            model=simulation_config.transposition,
            indeces=indeces,
            surface_tilt=surface_tilt,
            surface_azimuth=surface_azimuth,
            azimuth=solar_azimuth,
            apparent_zenith=solar_apparent_zenith,
            dhi=horizontal_irradiance.dhi,
            dni=horizontal_irradiance.dni,
            dni_extra=dni_extra,
            air_mass_relative=air_mass_relative,
        )

        ground_diffuse = GroundDiffuse(
            indeces=indeces,
            ghi=horizontal_irradiance.ghi,
            surface_tilt=surface_tilt,
            ALBEDO=ALBEDO,
        )

        beam = Beam(
            indeces=indeces,
            dni=horizontal_irradiance.dni,
            surface_tilt=surface_tilt,
            surface_azimuth=surface_azimuth,
            apparent_zenith=solar_apparent_zenith,
            azimuth=solar_azimuth,
        )

        rpoai = RearPlaneOfArrayIrradiance(
            model_rear_poa=simulation_config.rear_poa,
            indeces=indeces,
            ALBEDO=ALBEDO,
            AXIS_AZIMUTH=AXIS_AZIMUTH,
            apparent_zenith=solar_apparent_zenith,
            azimuth=solar_azimuth,
            surface_tilt=surface_tilt,
            surface_azimuth=surface_azimuth,
            ghi=horizontal_irradiance.ghi,
            dhi=horizontal_irradiance.dhi,
            dni=horizontal_irradiance.dni,
            dni_extra=dni_extra,
            racking_ids_by_string=racking_ids_by_string,
            racking_controls_gcr=racking_controls_gcr,
            racking_height=racking_height,
            module_ids_by_string=module_ids_by_string,
            pitch=pitch,
            module_bifaciality_factor=module_bifaciality_factor,
        )

        # --- Assignments ---
        self.beam = beam.beam
        self.isotropic = sky_diffuse.isotropic
        self.circumsolar = sky_diffuse.circumsolar
        self.horizon = sky_diffuse.horizon
        self.ground_diffuse = ground_diffuse.ground_diffuse
        self.rear = rpoai.rear
        self.gpoai = StringMetTimeSeries(
            pd.concat(
                [
                    self.beam,
                    self.isotropic,
                    self.circumsolar,
                    self.horizon,
                    self.ground_diffuse,
                    self.rear,
                ],
                axis=1,
            )
            .sum(axis=1)
            .rename("gpoai")
        )

        self.time = StringMetTimeSeries(indeces.string_met_time_index.loc[:, "time"])
        self.string_ids = StringMetTimeSeries(
            indeces.string_met_time_index.loc[:, "string_id"]
        )
        self.device_ids = StringMetTimeSeries(
            pd.merge(
                left=indeces.string_met_time_index.loc[:, "string_id"],
                right=pd.concat([indeces.string_index, combiner_ids_by_string], axis=1),
                how="left",
                on="string_id",
            )
            .loc[:, "combiner_device_id"]
            .rename("device_id")
        )
        self.tier = horizontal_irradiance.tier
        self.tier_codes = horizontal_irradiance.tier_codes

    def to_poai_df(self):
        """Convert POAI values to a DataFrame."""
        return pd.concat(
            [
                self.time,
                self.string_ids,
                self.rear,
                self.circumsolar,
                self.isotropic,
                self.horizon,
                self.ground_diffuse,
                self.beam,
            ],
            axis=1,
        )

    def to_poai_csv(
        self,
        target_string_id: int,
    ):
        """Write POAI values to CSV for one string."""
        df = self.to_poai_df()
        filtered_df = df[df["string_id"] == target_string_id]
        filtered_df.to_csv("poia.csv")
