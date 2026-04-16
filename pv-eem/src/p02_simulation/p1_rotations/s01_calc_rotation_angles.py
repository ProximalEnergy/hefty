import pandas as pd
import pvlib
from interfaces import Indeces, RackingEquipmentSeries, SystemSeries, TimeSeries
from p01_get_data.source_proximal.s04_get_system_data import RackingControlsAlgorithm
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.data_factorizer import factorize


def calc_rotation_angles(
    *,
    axis_azimuth: float,
    indeces: Indeces,
    solar_apparent_zenith: TimeSeries,
    solar_azimuth: TimeSeries,
    racking_controls_gcr: SystemSeries,
    racking_controls_algorithm: SystemSeries,
    racking_ids_by_string: SystemSeries,
    max_rotation_angle: RackingEquipmentSeries,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run calc_rotation_angles."""
    # --- HARDCODED ---
    AXIS_TILT = 0.0  # degrees
    CROSS_AXIS_TILT = 0.0  # degrees

    # --- Filter out system data ---
    inputs = merge_by_dimension(
        data_series=[
            racking_ids_by_string,
            racking_controls_gcr,
            racking_controls_algorithm,
            max_rotation_angle,
        ],
        merge_how=MergeHow.LEFT,
        indeces=indeces,
    )
    # --- CALCULATE RACKING GROUP ID ---
    # This will assign incrementing numbers to unique combinations of
    # tracker algorithm inputs
    inputs = factorize(
        dataframe=inputs,
        columns=[
            "racking_controls_algorithm",
            "max_rotation_angle",
            "racking_controls_gcr",
        ],
    )

    # only pull out unique combinations
    unique_by_group = inputs.groupby("_unique_id").first()
    unique_by_group = unique_by_group.reset_index()

    # set backtrack to false or true
    unique_by_group["backtrack"] = (
        unique_by_group["racking_controls_algorithm"]
        == RackingControlsAlgorithm.BACK_TRACKING_2D.value
    )

    # --- Merge Solar Position Data ---
    solar_position = pd.concat(
        [
            solar_apparent_zenith,
            solar_azimuth.rename("solar_azimuth"),
        ],
        axis=1,
    )
    unique_by_group = pd.merge(
        left=unique_by_group,
        right=solar_position,
        how="cross",
    )

    # --- FUNCTION ---
    group_ids = inputs["_unique_id"].unique()
    rotation_angle_groups = []
    for group_id in group_ids:
        group_inputs = unique_by_group.loc[unique_by_group["_unique_id"] == group_id]
        group_rotation_angles = pvlib.tracking.singleaxis(
            apparent_zenith=group_inputs["apparent_zenith"],
            solar_azimuth=group_inputs["solar_azimuth"],
            axis_tilt=AXIS_TILT,
            cross_axis_tilt=CROSS_AXIS_TILT,
            axis_azimuth=axis_azimuth,
            max_angle=group_inputs["max_rotation_angle"].iloc[0],
            backtrack=group_inputs["backtrack"].iloc[0],
            gcr=group_inputs["racking_controls_gcr"].iloc[0],
        )
        group_rotation_angles["time"] = pd.Series(indeces.time_index)
        group_rotation_angles["_unique_id"] = group_inputs["_unique_id"].iloc[0]

        rotation_angle_groups.append(group_rotation_angles)

    # --- Recombine ---
    rotation_angles = pd.concat(
        rotation_angle_groups,
    )

    return inputs["_unique_id"], rotation_angles
