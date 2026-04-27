from dataclasses import dataclass
from typing import Annotated

import pandas as pd
from interfaces import (
    Indeces,
    ModuleEquipmentSeries,
    RackingEquipmentSeries,
    StringMetTimeIndex,
    StringMetTimeSeries,
    TimeSeries,
)
from p01_get_data.source_proximal.s04_get_system_data import System
from p02_simulation.p1_rotations.s00_calc_if_backtracking import calc_if_backtracking
from p02_simulation.p1_rotations.s00_calc_pitch import calc_pitch
from p02_simulation.p1_rotations.s01_calc_rotation_angles import calc_rotation_angles
from p02_simulation.p1_rotations.s02_map_rotations_angles import map_rotations_to_mets


@dataclass(init=False, slots=True)
class RotationAngles:
    # Scalars
    """RotationAngles."""

    axis_azimuth: Annotated[
        float,
        "Axis azimuth angle in degrees where 180 degrees is South",
    ]

    # Series
    tracker_theta: StringMetTimeSeries
    surface_tilt: StringMetTimeSeries
    surface_azimuth: StringMetTimeSeries
    rotation_angle: StringMetTimeSeries
    aoi: StringMetTimeSeries

    def __init__(
        self,
        *,
        indeces: Indeces,
        AXIS_AZIMUTH: float,
        system: System,
        module_technology: ModuleEquipmentSeries,
        module_length: ModuleEquipmentSeries,
        max_rotation_angle: RackingEquipmentSeries,
        solar_apparent_zenith: TimeSeries,
        solar_azimuth: TimeSeries,
    ):
        # --- Assigns information to System instance ---
        calc_pitch(
            system=system,
            indeces=indeces,
            module_ids_by_string=system.module_equipment_id,
            racking_controls_gcr=system.racking_controls_gcr,
            module_length=module_length,
        )

        calc_if_backtracking(
            indeces=indeces,
            system=system,
            module_ids_by_string=system.module_equipment_id,
            module_technology=module_technology,
        )

        # --- Intermediates ---
        unique_ids, rotation_angles = calc_rotation_angles(
            axis_azimuth=AXIS_AZIMUTH,
            indeces=indeces,
            solar_apparent_zenith=solar_apparent_zenith,
            solar_azimuth=solar_azimuth,
            racking_controls_gcr=system.racking_controls_gcr,
            racking_controls_algorithm=system.racking_controls_algorithm,
            racking_ids_by_string=system.racking_equipment_id,
            max_rotation_angle=max_rotation_angle,
        )

        # --- IMPORTANT MERGE ---
        rotations = map_rotations_to_mets(
            indeces=indeces,
            system=system,
            unique_ids=unique_ids.copy(),
            rotation_angles=rotation_angles.copy(),
        )

        # Initialize Self
        self.axis_azimuth = AXIS_AZIMUTH
        self.tracker_theta = StringMetTimeSeries(rotations.loc[:, "tracker_theta"])
        self.surface_tilt = StringMetTimeSeries(rotations.loc[:, "surface_tilt"])
        self.surface_azimuth = StringMetTimeSeries(rotations.loc[:, "surface_azimuth"])
        self.rotation_angle = StringMetTimeSeries(rotations.loc[:, "tracker_theta"])
        self.aoi = StringMetTimeSeries(rotations.loc[:, "aoi"])

        # Filter rotations to only include met_names that are in indeces.met_time_index
        allowed_met_names = list(indeces.met_time_index["met_name"].unique())
        filtered_rotations = rotations[rotations["met_name"].isin(allowed_met_names)]

        indeces.string_met_time_index = StringMetTimeIndex(
            filtered_rotations.loc[:, ["string_id", "met_name", "time"]]
        )

    def to_rotation_angles_df(self, indeces):
        """Convert rotation angles to a DataFrame."""
        return pd.DataFrame(
            {
                "time": indeces.time_index,
                "tracker_theta": self.tracker_theta,
                "surface_tilt": self.surface_tilt,
                "surface_azimuth": self.surface_azimuth,
                "rotation_angle": self.rotation_angle,
                "aoi": self.aoi,
            }
        )

    def to_rotation_angles_csv(self, indeces):
        """Write rotation angles to CSV."""
        df = self.to_rotation_angles_df(indeces)
        df.to_csv("rotation_angles.csv", index=False)
