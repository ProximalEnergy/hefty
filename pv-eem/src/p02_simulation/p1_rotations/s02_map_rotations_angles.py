import pandas as pd
from interfaces import Indeces
from p01_get_data.source_proximal.s04_get_system_data import (
    System,
)


def map_rotations_to_mets(
    *,
    indeces: Indeces,
    system: System,
    unique_ids: pd.Series,
    rotation_angles: pd.DataFrame,
):
    # --- COMPOSE ---
    """Run map_rotations_to_mets."""
    df = pd.concat(
        [
            system.string_id,
            system.met_name,
            unique_ids,
        ],
        axis=1,
    )

    # --- FILTER ---
    # remove met's that are not in met_time_index
    df = df.loc[df["met_name"].isin(indeces.met_time_index.loc[:, "met_name"])]

    # --- MERGE ---
    # This is the most important merge in the entire simulation
    # It maps the system data to the timeseries
    inputs = pd.merge(
        left=df[["string_id", "_unique_id", "met_name"]],
        right=rotation_angles[
            [
                "_unique_id",
                "time",
                "tracker_theta",
                "surface_tilt",
                "surface_azimuth",
                "aoi",
            ]
        ],
        on="_unique_id",
        how="left",
    )

    return inputs
