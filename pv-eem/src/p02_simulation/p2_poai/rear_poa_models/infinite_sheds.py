import pandas as pd
from pvlib.bifacial.infinite_sheds import _backside, get_irradiance_poa


def calculate_rear_irradiance_infinite_sheds(
    *,
    bifacial_inputs: pd.DataFrame,
    ALBEDO: float,
) -> pd.Series:
    """Infinite sheds model from pvlib has serious bugs, see:
    https://github.com/pvlib/pvlib-python/issues/2541
    """
    # Reverse surface angles to get the rear-side orientation
    (
        bifacial_inputs["rear_surface_tilt"],
        bifacial_inputs["rear_surface_azimuth"],
    ) = _backside(
        tilt=bifacial_inputs["surface_tilt"],
        surface_azimuth=bifacial_inputs["surface_azimuth"],
    )

    # Define columns that must be passed as scalar floats to the pvlib function
    # These will be our grouping keys.
    grouping_cols = ["racking_controls_gcr", "pile_height", "pitch"]

    results_list: list[pd.DataFrame] = []

    # Loop over each unique combination of scalar inputs
    for _, group_df in bifacial_inputs.groupby(grouping_cols):
        gcr = group_df["racking_controls_gcr"].iloc[0]
        height = group_df["pile_height"].iloc[0]
        pitch = group_df["pitch"].iloc[0]

        # Call the pvlib function for this subset of data
        rear_irradiance_group = get_irradiance_poa(
            surface_tilt=group_df["rear_surface_tilt"],
            surface_azimuth=group_df["rear_surface_azimuth"],
            solar_zenith=group_df["apparent_zenith"],
            solar_azimuth=group_df["azimuth"],
            gcr=gcr,
            height=height,
            pitch=pitch,
            ghi=group_df["ghi"],
            dhi=group_df["dhi"],
            dni=group_df["dni"],
            albedo=ALBEDO,
            model="hay_davies",
            dni_extra=group_df["dni_extra"],
            iam=1.0,
            npoints=6,
            vectorize=True,
        )
        results_list.append(rear_irradiance_group)

    # Combine the results from all groups
    rear_irradiance_bifacial = pd.concat(results_list)
    poa_rear_series = rear_irradiance_bifacial["poa_ground_diffuse"]

    return poa_rear_series
