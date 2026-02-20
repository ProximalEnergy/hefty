import logging
import os
from typing import TYPE_CHECKING

import polars as pl
from p02_simulation._utils.known_exception import (
    KnownException,
    KnownExceptionType,
)

if TYPE_CHECKING:
    from p01_get_data.source_proximal.s04_get_system_data import System


def qc_combined_data(
    *,
    combined_data: pl.DataFrame,
    system: "System",
    use_poa_only: bool,
    use_median_irr_sensor: bool = False,
) -> pl.DataFrame:
    """Quality control for combined met and soiling data:
        * Replaces POA values with median if z-score > 10
        * Overwrites irradiance columns with median if requested
        * Replaces nulls with timestep average for all mets
        * Adds missing met stations from system with averaged data
        * Adds quality columns (tier, tier_codes)
        * Fills missing columns with default values
        * Removes rows where GHI < 5 W/m^2 (if not use_poa_only)
        * Removes rows where ambient temperature is NaN
        * Validates required columns exist
        * Validates dataframe is not empty
    Args:
        * combined_data: Combined met and soiling data
        * system: system definition containing met station names
        * use_poa_only: whether to use POA only
        * use_median_irr_sensor: whether to use median instead of mean for
          irradiance aggregation
    Returns:
        * combined_data: QC'd combined data
    """
    # --- REPLACE POA OUTLIERS WITH MEDIAN (z-score > 10) ---
    STANDARD_DEVIATION_THRESHOLD = 10.0
    MINIMUM_SENSOR_COUNT = 3
    if "poa" in combined_data.columns:
        # Calculate median, std dev, and count for POA at each timestep
        # (excluding zeros)
        poa_stats = combined_data.group_by("time").agg(
            [
                pl.col("poa").filter(pl.col("poa") > 0).std().alias("poa_std"),
                pl.col("poa").filter(pl.col("poa") > 0).median().alias("poa_median"),
                pl.col("poa").filter(pl.col("poa") > 0).count().alias("poa_count"),
            ]
        )

        # Join stats back to data
        combined_data = combined_data.join(poa_stats, on="time", how="left")

        # Calculate z-score and replace outliers (only if >= 3 non-zero
        # sensors at timestep)
        combined_data = combined_data.with_columns(
            pl.when(
                (pl.col("poa_count") >= MINIMUM_SENSOR_COUNT)
                & (pl.col("poa") > 0)
                & (
                    ((pl.col("poa") - pl.col("poa_median")).abs() / pl.col("poa_std"))
                    > STANDARD_DEVIATION_THRESHOLD
                )
            )
            .then(pl.col("poa_median"))
            .otherwise(pl.col("poa"))
            .alias("poa")
        ).drop(["poa_std", "poa_median", "poa_count"])

    # --- OVERWRITE IRRADIANCE COLUMNS WITH MEDIAN IF REQUESTED ---
    if use_median_irr_sensor:
        # Determine which irradiance columns are present
        irr_cols = [
            col
            for col in ["ghi", "ghi_tilt", "poa", "poa_tilt"]
            if col in combined_data.columns
        ]

        # Calculate median for each irradiance column by time
        median_values = combined_data.group_by("time").agg(
            [pl.col(col).median().alias(f"{col}_median") for col in irr_cols]
        )

        # Join median values back and overwrite original irradiance columns
        combined_data = combined_data.join(
            median_values,
            on="time",
        )
        for col in irr_cols:
            combined_data = combined_data.with_columns(
                pl.col(f"{col}_median").alias(col),
            ).drop(f"{col}_median")

    # --- REPLACE NULLS WITH TIMESTEP AVERAGE FOR ALL METS ---
    # Get list of columns to process (exclude 'time' and 'met_name')
    value_columns = [
        col for col in combined_data.columns if col not in ["time", "met_name"]
    ]

    # Create expressions for filling nulls
    fill_expressions = []
    for col in value_columns:
        # Use median for irradiance columns if specified
        if use_median_irr_sensor and col in ["ghi", "poa"]:
            fill_expressions.append(
                pl.col(col).fill_null(pl.col(col).median().over("time")).alias(col)
            )
        else:
            fill_expressions.append(
                pl.col(col).fill_null(pl.col(col).mean().over("time")).alias(col)
            )

    # Apply the transformations
    combined_data_without_nulls = combined_data.select(
        [pl.col("time"), pl.col("met_name"), *fill_expressions]
    )

    # --- Average Missing Met Data ---
    logging.info("Averaging missing met data...")
    system_met_names = system.met_name.unique()
    all_times = combined_data_without_nulls["time"].unique().sort()

    # 1. Create the complete grid (scaffold) of all time/met station combinations.
    scaffold = pl.DataFrame(
        {
            "time": all_times,
        }
    ).join(
        pl.DataFrame({"met_name": system_met_names}),
        how="cross",
    )

    data_with_missing_rows = scaffold.join(
        combined_data_without_nulls,
        on=["time", "met_name"],
        how="left",
    )

    # Use median for irradiance columns if specified, otherwise use mean
    fill_expressions = []
    for col in value_columns:
        if use_median_irr_sensor and col in ["ghi", "poa"]:
            fill_expressions.append(
                pl.col(col).fill_null(pl.col(col).median().over("time"))
            )
        else:
            fill_expressions.append(
                pl.col(col).fill_null(pl.col(col).mean().over("time"))
            )

    # Apply the transformations
    final_filled_data = data_with_missing_rows.select(
        "time",
        "met_name",
        *fill_expressions,
    )

    # --- Add Quality Columns ---
    combined_data = final_filled_data.with_columns(
        [pl.lit(1).alias("tier"), pl.lit("").alias("tier_codes")]
    )

    # --- Fill Missing Columns ---
    # Add default columns if they don't exist
    if "soil_percent" not in combined_data.columns:
        logging.warning("... soil percent data missing, hard-coding to no soiling")
        combined_data = combined_data.with_columns(
            pl.lit(1.0).alias("soil_percent"),
        )  # Default no soiling (1.0 = 100% transmission)
        combined_data = combined_data.with_columns(
            [
                (pl.col("tier_codes") + "soil_missing,").alias("tier_codes"),
                pl.lit(3).alias("tier"),
            ]
        )

    # Check if soil_percent column exists but has NaN values
    if combined_data.filter(pl.col("soil_percent").is_null()).height > 0:
        logging.warning(
            "... some soil_percent values are NaN, replacing with no soiling"
        )
        combined_data = combined_data.with_columns(
            pl.col("soil_percent").fill_null(1.0).alias("soil_percent"),
        )
        combined_data = combined_data.with_columns(
            [
                (pl.col("tier_codes") + "soil_missing,").alias("tier_codes"),
                pl.lit(3).alias("tier"),
            ]
        )

    # Add default columns if they don't exist
    if "relative_humidity" not in combined_data.columns:
        logging.warning("... relative humidity data missing, hard-coding to 50%")
        combined_data = combined_data.with_columns(
            pl.lit(50.0).alias("relative_humidity"),
        )  # Default 50% humidity
        combined_data = combined_data.with_columns(
            [
                (pl.col("tier_codes") + "rh_missing,").alias("tier_codes"),
                pl.lit(3).alias("tier"),
            ]
        )

    # Check if relative_humidity column exists but has NaN values
    if combined_data.filter(pl.col("relative_humidity").is_null()).height > 0:
        logging.warning("... some relative humidity values are NaN, replacing with 50%")
        combined_data = combined_data.with_columns(
            pl.col("relative_humidity").fill_null(50.0).alias("relative_humidity"),
        )
        combined_data = combined_data.with_columns(
            [
                (pl.col("tier_codes") + "rh_missing,").alias("tier_codes"),
                pl.lit(3).alias("tier"),
            ]
        )

    if "wind_speed" not in combined_data.columns:
        logging.warning("... wind_speed data missing, hard-coding to 0 m/s")
        combined_data = combined_data.with_columns(
            pl.lit(0.0).alias("wind_speed"),
        )  # Default 0 m/s wind speed
        combined_data = combined_data.with_columns(
            [
                (pl.col("tier_codes") + "wind_speed_missing,").alias("tier_codes"),
                pl.lit(3).alias("tier"),
            ]
        )

    # Check if wind_speed column exists but has NaN values
    if combined_data.filter(pl.col("wind_speed").is_null()).height > 0:
        logging.warning("... some wind_speed values are NaN, replacing with 0 m/s")
        combined_data = combined_data.with_columns(
            pl.col("wind_speed").fill_null(0.0).alias("wind_speed"),
        )
        combined_data = combined_data.with_columns(
            [
                (pl.col("tier_codes") + "wind_speed_missing,").alias("tier_codes"),
                pl.lit(3).alias("tier"),
            ]
        )

    if "poa_tilt" not in combined_data.columns:
        logging.warning("... poa_tilt data missing, hard-coding to -999")
        combined_data = combined_data.with_columns(
            pl.lit(-999.0).alias("poa_tilt"),
        )  # Default -999 for missing poa_tilt
        combined_data = combined_data.with_columns(
            [
                (pl.col("tier_codes") + "poa_tilt_missing,").alias("tier_codes"),
                pl.lit(3).alias("tier"),
            ]
        )

    # Check if poa_tilt column exists but has NaN values
    if combined_data.filter(pl.col("poa_tilt").is_null()).height > 0:
        logging.warning("... some poa_tilt values are NaN, replacing with -999")
        combined_data = combined_data.with_columns(
            pl.col("poa_tilt").fill_null(-999.0).alias("poa_tilt"),
        )
        combined_data = combined_data.with_columns(
            [
                (pl.col("tier_codes") + "poa_tilt_missing,").alias("tier_codes"),
                pl.lit(3).alias("tier"),
            ]
        )

    # --- REMOVE ROWS WHERE GHI is < 5 W/m^2 ---
    if not use_poa_only:
        combined_data = combined_data.filter(pl.col("ghi") >= 5)

    # --- REMOVE ROWS WHERE AMBIENT TEMPERATURE IS NAN ---
    combined_data = combined_data.filter(
        pl.col("ambient_temperature").is_not_null(),
    )

    # --- QC ---
    # Check to see that irradiance and Ambient Temperature columns exist
    irradiance_column_name = "ghi"
    if use_poa_only:
        irradiance_column_name = "poa"
        combined_data = combined_data.with_columns(
            pl.lit(-999.0).alias("ghi"),
        )
    match irradiance_column_name in combined_data.columns:
        case True:
            pass
        case False:
            logging.critical(f"...Missing required column: {irradiance_column_name}")
            raise KnownException(
                error_type=KnownExceptionType.NO_IRRADIANCE,
                message=(
                    "No irradiance data for time period,"
                    "possibly night [1]"
                    f"--> {os.path.basename(__file__)}"
                ),
            )

    match "ambient_temperature" in combined_data.columns:
        case True:
            pass
        case False:
            logging.critical("...Missing required column: ambient_temperature")
            raise KnownException(
                error_type=KnownExceptionType.NO_AMBIENT_TEMPERATURE,
                message="No GHI data for time period, possibly night",
            )

    # Check that the dataframe is not empty again
    match combined_data.shape[0] > 0:
        case True:
            pass
        case False:
            logging.info("...No Met Data for Time Period")
            raise KnownException(
                error_type=KnownExceptionType.NO_IRRADIANCE,
                message=(
                    "No irradiance data for time period,"
                    "possibly night [2]"
                    f"--> {os.path.basename(__file__)}"
                ),
            )

    return combined_data
