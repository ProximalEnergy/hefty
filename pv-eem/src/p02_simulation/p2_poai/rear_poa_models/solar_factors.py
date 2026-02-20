import pandas as pd
from pvfactors.engine import PVEngine
from pvfactors.geometry import OrderedPVArray


def calculate_rear_irradiance_solar_factors(
    *,
    bifacial_inputs: pd.DataFrame,
    AXIS_AZIMUTH: float,
    ALBEDO: float,
) -> pd.Series:
    # --- CONSTANTS ---
    """Run calculate_rear_irradiance_solar_factors."""
    N_PVROWS = 5

    # --- GROUPS ---
    grouping_cols = ["racking_controls_gcr", "pile_height", "pitch"]

    # Initialize results series with the same index as input
    poa_rear_series = pd.Series(
        index=bifacial_inputs.index, dtype=float, name="qinc_back"
    )

    for group_indices, group_df in bifacial_inputs.groupby(grouping_cols):
        gcr = group_df["racking_controls_gcr"].iloc[0]
        height = group_df["pile_height"].iloc[0]
        pitch = group_df["pitch"].iloc[0]
        pvrow_width = pitch * gcr

        pv_array_parameters = {
            "n_pvrows": N_PVROWS,
            "pvrow_height": height,
            "pvrow_width": pvrow_width,
            "axis_azimuth": AXIS_AZIMUTH,
            "gcr": gcr,
        }

        pvarray = OrderedPVArray.init_from_dict(pv_array_parameters)
        engine = PVEngine(pvarray)
        engine.fit(
            timestamps=group_df["time"],
            DNI=group_df["dni"],
            DHI=group_df["dhi"],
            solar_zenith=group_df["apparent_zenith"],
            solar_azimuth=group_df["azimuth"],
            surface_tilt=group_df["surface_tilt"],
            surface_azimuth=group_df["surface_azimuth"],
            albedo=ALBEDO,
        )

        # Run the fast mode calculation on the middle PV row
        df_report: pd.DataFrame | None = engine.run_full_mode(
            fn_build_report=_fn_report,
        )
        if df_report is not None and not df_report.empty:
            # Assign results back to the original indices for this group
            poa_rear_series.loc[group_df.index] = df_report["qinc_back"].values

    return poa_rear_series


def _fn_report(pvarray):
    return pd.DataFrame(
        {"qinc_back": pvarray.ts_pvrows[1].back.get_param_weighted("qinc")}
    )
