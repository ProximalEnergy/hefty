import polars as pl


def combine_met_and_soiling_data(
    *,
    met_data: pl.DataFrame,
    soiling_data: pl.DataFrame,
    time_zone: str,
) -> pl.DataFrame:
    """Combines met and soiling data:
        * adding soiling data
        * time-shifting to local time
    Args:
        * met_data:  met data after QC
        * soiling_data: soiling data
        * time_zone: timezone string
    Returns:
        * combined_data:  Combined met and soiling data in polars format
    """
    # --- Add soiling data ---
    # See if soiling_data is empty
    match soiling_data.shape[0] > 0:
        case True:
            # First get averages of soil_percent for each met_name
            soiling_data = soiling_data.group_by(["met_name"]).agg(
                [
                    pl.col("soil_percent").mean().alias("soil_percent"),
                ]
            )

            # Perform the join
            combined_data: pl.DataFrame = met_data.join(
                soiling_data[["met_name", "soil_percent"]],
                on=["met_name"],
                how="left",  # Keeps all records from met_data
            )

        case False:
            combined_data = met_data.clone()

    # --- Localize to project timezone ---
    combined_data_localized: pl.DataFrame = combined_data.with_columns(
        [
            pl.col("time")
            .cast(pl.Datetime)
            .dt.replace_time_zone("UTC")
            .dt.convert_time_zone(time_zone)
            .alias("time")
        ]
    )

    return combined_data_localized
