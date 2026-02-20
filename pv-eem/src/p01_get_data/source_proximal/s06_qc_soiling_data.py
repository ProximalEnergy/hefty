import logging
import os

import polars as pl
from p02_simulation._utils.known_exception import (
    KnownException,
    KnownExceptionType,
)
from p02_simulation.p3_epoai.s05_soiling import ModelSoiling


def qc_soiling_data(
    soiling_data_raw: pl.DataFrame,
    soiling_model: ModelSoiling,
    use_poa_only: bool,
) -> pl.DataFrame:
    """Formats soiling data by:
        * Removing rows where soiling is outside thresholds
        * Filtering out GHI < 100.0
        * Setting the ceiling of the remaining data to 1
        * Filtering out the lowest 25% of the soiling data
    Args:
        * soiling_data_raw:  Raw soiling data
        * met_data_raw:  Raw met data for GHI filter
    """
    # --- Checks ---
    # Check that the dataframe is not empty
    match soiling_data_raw.shape[0] > 0:
        case True:
            pass
        case False:
            return soiling_data_raw

    # Check if "met_station_ghi" exists in the "sensor_name" column
    irradiance_name = "met_station_ghi"
    if use_poa_only:
        irradiance_name = "met_station_poa"
    irr_data_present = (
        soiling_data_raw["sensor_name"].str.contains(irradiance_name).any()
    )
    match irr_data_present:
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

    # Check if "met_station_soil_percent" exists in the "sensor_name" column
    soiling_data_present = (
        soiling_data_raw["sensor_name"].str.contains("met_station_soil_percent").any()
    )
    if soiling_model == ModelSoiling.NONE:
        return pl.DataFrame()
    elif (soiling_model == ModelSoiling.MEASURED) and soiling_data_present:
        pass
    elif (soiling_model == ModelSoiling.MEASURED) and not soiling_data_present:
        logging.info("...No Soiling Data for Time Period")
        raise KnownException(
            error_type=KnownExceptionType.NO_SOILING,
            message="No Soiling data for time period",
        )
    else:
        raise ValueError("This soiling scenario is not supported")

    # --- Convert to columnar format ---
    # Remove met_station_ from column name
    soiling_data = soiling_data_raw.with_columns(
        pl.col("sensor_name").str.slice(offset=len("met_station_"))
    )
    # pivot table so that sensors become columns and devices become indexes
    soiling_data = soiling_data.pivot(
        on="sensor_name",
        index=["time", "met_name"],
        values="value_continuous",
    )

    # Ensure that there is soil_percent data for each met_name-time pair by forward
    # and backward filling
    soiling_data_soil_percent = soiling_data.pivot(
        on="met_name",
        index="time",
        values="soil_percent",
    )
    soiling_data_soil_percent = soiling_data_soil_percent.select(
        pl.all().forward_fill()
    )
    soiling_data_soil_percent = soiling_data_soil_percent.select(
        pl.all().backward_fill()
    )

    # Merge soiling percent data with soiling data
    soiling_data_soil_percent = soiling_data_soil_percent.unpivot(
        pl.selectors.numeric(),
        index="time",
        variable_name="met_name",
        value_name="soil_percent",
    )
    soiling_data = soiling_data.update(
        soiling_data_soil_percent,
        on=["time", "met_name"],
        how="left",
    )

    # --- QC ---
    # Step 0: Remove rows where soiling is outside thresholds
    # NOTE: These are manually selected thresholds based on data we think we can expect
    soiling_threshold_low = 0.5  # 50%
    soiling_threshold_high = 1.03  # 103%
    soiling_data = soiling_data.filter(pl.col("soil_percent") >= soiling_threshold_low)
    soiling_data = soiling_data.filter(pl.col("soil_percent") <= soiling_threshold_high)

    # Step 1: Filter out Irradiance < threshold
    threshold_column = "ghi"
    threshold_value = 100.0
    if use_poa_only:
        threshold_column = "poa"
        threshold_value = 50.0
    soiling_data = soiling_data.filter(pl.col(threshold_column) >= threshold_value)

    # Step 2: Set the ceiling of the remaining data to 1
    soiling_data = soiling_data.with_columns(
        pl.col("soil_percent").clip(upper_bound=1).alias("soil_percent")
    )

    # Step 3: Filter out the lowest 25% of the soiling data
    soiling_data = soiling_data.filter(
        pl.col("soil_percent") >= pl.col("soil_percent").quantile(0.25)
    )

    return soiling_data
