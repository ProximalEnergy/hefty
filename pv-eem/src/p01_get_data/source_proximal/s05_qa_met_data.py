import os

import polars as pl
from p02_simulation._utils.known_exception import (
    KnownException,
    KnownExceptionType,
)


def qa_met_data(
    met_data_raw: pl.DataFrame,
    use_poa_only: bool,
) -> pl.DataFrame:
    """Run qa_met_data."""
    # Check that the dataframe is not empty
    match met_data_raw.shape[0] > 0:
        case True:
            pass
        case False:
            raise KnownException(
                error_type=KnownExceptionType.NO_IRRADIANCE,
                message=(
                    "No irradiance data for time period,"
                    "possibly night [1]"
                    f"--> {os.path.basename(__file__)}"
                ),
            )

    # Check if "met_station_ghi" exists in the "sensor_name" column
    irr_sensor_name = "met_station_ghi"
    if use_poa_only:
        irr_sensor_name = "met_station_poa"
    irr_data_present = met_data_raw["sensor_name"].str.contains(irr_sensor_name).any()
    match irr_data_present:
        case True:
            pass
        case False:
            raise KnownException(
                error_type=KnownExceptionType.NO_IRRADIANCE,
                message=(
                    "No irradiance data for time period,"
                    "possibly night [2]"
                    f"--> {os.path.basename(__file__)}"
                ),
            )

    t_amb_data_present = (
        met_data_raw["sensor_name"]
        .str.contains("met_station_ambient_temperature")
        .any()
    )
    match t_amb_data_present:
        case True:
            pass
        case False:
            raise KnownException(
                error_type=KnownExceptionType.NO_AMBIENT_TEMPERATURE,
                message=(
                    "No ambient temperature data for time period"
                    f"--> {os.path.basename(__file__)}"
                ),
            )

    # --- Convert to columnar format ---
    # Remove met_station_ from column name
    met_data_raw = met_data_raw.with_columns(
        pl.col("sensor_name").str.slice(offset=len("met_station_"))
    )
    # pivot table so that sensors become columns and devices become indexes
    met_data_raw = met_data_raw.pivot(
        on="sensor_name",
        index=["time", "met_name"],
        values="value_continuous",
    )

    # Check if poa_tilt column exists, if not hardcode to -999 and set tier to 2
    if "poa_tilt" not in met_data_raw.columns:
        met_data_raw = met_data_raw.with_columns(
            [pl.lit(-999).alias("poa_tilt"), pl.lit(2).alias("tier")]
        )

    # Set 0 POA values to NaN only if there are non-zero POA values in the
    # dataset. This prevents converting all nighttime zeros to NaN.
    if "poa" in met_data_raw.columns:
        has_nonzero_poa = met_data_raw.select(pl.col("poa").gt(0).any()).item()
        if has_nonzero_poa:
            met_data_raw = met_data_raw.with_columns(
                pl.when(pl.col("poa") == 0)
                .then(None)
                .otherwise(pl.col("poa"))
                .alias("poa")
            )

    return met_data_raw
