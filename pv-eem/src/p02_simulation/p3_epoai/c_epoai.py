from dataclasses import dataclass

import pandas as pd
from interfaces import (
    Indeces,
    MetTimeSeries,
    ModuleEquipmentSeries,
    RackingEquipmentSeries,
    StringMetTimeSeries,
    SystemSeries,
    TimeSeries,
)
from p01_get_data.s00_get_simulation_config import SimulationConfig
from p02_simulation.p2_poai.c_poai import PlaneOfArrayIrradiance
from p02_simulation.p3_epoai.s01_direct_shade import EPOAIafterFrontShade
from p02_simulation.p3_epoai.s02_electrical_effect import EPOAIfterElectricalEffect
from p02_simulation.p3_epoai.s03_diffuse_shade import EPOAIafterDiffuseShade
from p02_simulation.p3_epoai.s04_rear_shade import EPOAIafterRearShade
from p02_simulation.p3_epoai.s05_soiling import EPOAIafterSoiling
from p02_simulation.p3_epoai.s06_direct_iam import EPOAIafterDirectIAM
from p02_simulation.p3_epoai.s07_diffuse_iam import EPOAIafterDiffuseIAM
from p02_simulation.p3_epoai.s08_spectral import EPOAIafterSpectral


@dataclass(init=False, slots=True)
class EffectivePlaneOfArrayIrradiance:
    """EffectivePlaneOfArrayIrradiance."""

    gpoai: StringMetTimeSeries
    beam: StringMetTimeSeries
    horizon: StringMetTimeSeries
    circumsolar: StringMetTimeSeries
    isotropic: StringMetTimeSeries
    ground_diffuse: StringMetTimeSeries
    rear: StringMetTimeSeries

    def __init__(
        self,
        simulation_config: SimulationConfig,
        indeces: Indeces,
        poai: PlaneOfArrayIrradiance,
        apparent_zenith: TimeSeries,
        azimuth: TimeSeries,
        tracker_theta: StringMetTimeSeries,
        surface_tilt: StringMetTimeSeries,
        aoi: StringMetTimeSeries,
        soil_percent: MetTimeSeries,
        module_id_by_string: SystemSeries,
        racking_id_by_string: SystemSeries,
        pitch: SystemSeries,
        racking_controls_gcr: SystemSeries,
        module_length: ModuleEquipmentSeries,
        module_technology: ModuleEquipmentSeries,
        module_is_half_cut: ModuleEquipmentSeries,
        module_has_ar_coating: ModuleEquipmentSeries,
        module_bifaciality_factor: ModuleEquipmentSeries,
        racking_structure_shade_factor: RackingEquipmentSeries,
        racking_rear_mismatch_factor: RackingEquipmentSeries,
        air_mass_absolute: TimeSeries,
        precipitable_water: MetTimeSeries,
        AXIS_AZIMUTH: float,
    ):
        epoai_after_front_shade = EPOAIafterFrontShade(
            model_circumsolar=simulation_config.circumsolar,
            indeces=indeces,
            poai=poai,
            apparent_zenith=apparent_zenith,
            azimuth=azimuth,
            pitch=pitch,
            tracker_theta=tracker_theta,
            module_id_by_string=module_id_by_string,
            module_length=module_length,
            axis_azimuth=AXIS_AZIMUTH,
        )

        epoai_electrical_effect = EPOAIfterElectricalEffect(
            epoai_after_front_shade=epoai_after_front_shade,
            indeces=indeces,
            module_id_by_string=module_id_by_string,
            module_technology=module_technology,
            module_is_half_cut=module_is_half_cut,
        )

        epoai_diffuse_shade = EPOAIafterDiffuseShade(
            model_circumsolar=simulation_config.circumsolar,
            epoai_after_electrical_effect=epoai_electrical_effect,
            indeces=indeces,
            racking_controls_gcr=racking_controls_gcr,
            surface_tilt=surface_tilt,
        )

        epoai_rear_shade = EPOAIafterRearShade(
            epoai_after_diffuse_shade=epoai_diffuse_shade,
            indeces=indeces,
            racking_id_by_string=racking_id_by_string,
            structure_shading_factor=racking_structure_shade_factor,
            rear_mismatch_factor=racking_rear_mismatch_factor,
            module_id_by_string=module_id_by_string,
            bifaciality_factor=module_bifaciality_factor,
        )

        epoai_soiling = EPOAIafterSoiling(
            model=simulation_config.soiling,
            indeces=indeces,
            epoai_rear_shade=epoai_rear_shade,
            soil_percent=soil_percent,
        )

        epoai_direct_iam = EPOAIafterDirectIAM(
            model_iam=simulation_config.iam,
            model_circumsolar=simulation_config.circumsolar,
            indeces=indeces,
            epoai_soiling=epoai_soiling,
            module_id_by_string=module_id_by_string,
            module_has_ar_coating=module_has_ar_coating,
            aoi=aoi,
        )

        epoai_diffuse_iam = EPOAIafterDiffuseIAM(
            model_circumsolar=simulation_config.circumsolar,
            epoai_direct_iam=epoai_direct_iam,
            indeces=indeces,
            surface_tilt=surface_tilt,
        )

        epoai_spectral = EPOAIafterSpectral(
            model_spectral=simulation_config.spectral,
            indeces=indeces,
            epoai_diffuse_iam=epoai_diffuse_iam,
            module_id_by_string=module_id_by_string,
            module_technology=module_technology,
            air_mass_absolute=air_mass_absolute,
            precipitable_water=precipitable_water,
        )

        self.beam = epoai_spectral.beam
        self.circumsolar = epoai_spectral.circumsolar
        self.isotropic = epoai_spectral.isotropic
        self.horizon = epoai_spectral.horizon
        self.ground_diffuse = epoai_spectral.ground_diffuse
        self.rear = epoai_spectral.rear

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
            .rename("global")
        )

    def to_epoai_df(self, indeces):
        """Convert EPOAI values to a DataFrame."""
        return pd.DataFrame(
            {
                "time": indeces.string_met_time_index.loc[:, "time"],
                "met": indeces.string_met_time_index.loc[:, "met_name"],
                "string_id": indeces.string_met_time_index.loc[:, "string_id"],
                "beam": self.beam.values,
                "circumsolar": self.circumsolar.values,
                "isotropic": self.isotropic.values,
                "horizon": self.horizon.values,
                "ground_diffuse": self.ground_diffuse.values,
                "rear": self.rear.values,
                "global": self.gpoai.values,
            }
        )

    def to_epoai_csv(self, indeces):
        """Write EPOAI values to CSV."""
        df = self.to_epoai_df(indeces)
        df.to_csv("epoai.csv", index=False)
