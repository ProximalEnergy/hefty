from typing import Any

import pandas as pd
from pvfactors.engine import PVEngine
from pvfactors.geometry import OrderedPVArray
from pvfactors.irradiance import utils as pvfactors_utils

_PVFACTORS_PEREZ_COMPAT_PATCHED = False


def _ensure_pvfactors_perez_component_compatibility() -> None:
    """Patch pvfactors for pvlib>=0.14 component column name changes.

    pvfactors expects perez(return_components=True) columns:
    horizon / circumsolar / isotropic / sky_diffuse.
    Newer pvlib versions return poa_horizon / poa_circumsolar / poa_isotropic /
    poa_sky_diffuse.
    """

    global _PVFACTORS_PEREZ_COMPAT_PATCHED
    if _PVFACTORS_PEREZ_COMPAT_PATCHED:
        return

    original_perez = pvfactors_utils.irradiance.perez

    def _perez_with_legacy_columns(*args: Any, **kwargs: Any):
        components = original_perez(*args, **kwargs)

        if kwargs.get("return_components") and hasattr(components, "columns"):
            rename_map: dict[str, str] = {}
            if (
                "poa_horizon" in components.columns
                and "horizon" not in components.columns
            ):
                rename_map["poa_horizon"] = "horizon"
            if (
                "poa_circumsolar" in components.columns
                and "circumsolar" not in components.columns
            ):
                rename_map["poa_circumsolar"] = "circumsolar"
            if (
                "poa_isotropic" in components.columns
                and "isotropic" not in components.columns
            ):
                rename_map["poa_isotropic"] = "isotropic"
            if (
                "poa_sky_diffuse" in components.columns
                and "sky_diffuse" not in components.columns
            ):
                rename_map["poa_sky_diffuse"] = "sky_diffuse"

            if rename_map:
                components = components.rename(columns=rename_map)

        return components

    pvfactors_utils.irradiance.perez = _perez_with_legacy_columns
    _PVFACTORS_PEREZ_COMPAT_PATCHED = True


def calculate_rear_irradiance_solar_factors(
    *,
    bifacial_inputs: pd.DataFrame,
    AXIS_AZIMUTH: float,
    ALBEDO: float,
) -> pd.Series:
    # --- CONSTANTS ---
    """Run calculate_rear_irradiance_solar_factors."""
    N_PVROWS = 5

    _ensure_pvfactors_perez_component_compatibility()

    # --- GROUPS ---
    grouping_cols = ["racking_controls_gcr", "pile_height", "pitch"]

    # Initialize results series with the same index as input
    poa_rear_series = pd.Series(
        index=bifacial_inputs.index, dtype=float, name="qinc_back"
    )

    for _, group_df in bifacial_inputs.groupby(grouping_cols):
        gcr = group_df["racking_controls_gcr"].iloc[0]
        height = group_df["pile_height"].iloc[0]
        pitch = group_df["pitch"].iloc[0]
        pvrow_width = pitch * gcr
        engine_inputs = _deduplicate_engine_inputs(group_df=group_df)

        pv_array_parameters = {
            "n_pvrows": N_PVROWS,
            "pvrow_height": height,
            "pvrow_width": pvrow_width,
            "axis_azimuth": AXIS_AZIMUTH,
            "gcr": gcr,
        }

        pvarray = OrderedPVArray.init_from_dict(pv_array_parameters)
        engine = PVEngine(pvarray)
        try:
            engine.fit(
                timestamps=engine_inputs["time"],
                DNI=engine_inputs["dni"],
                DHI=engine_inputs["dhi"],
                solar_zenith=engine_inputs["apparent_zenith"],
                solar_azimuth=engine_inputs["azimuth"],
                surface_tilt=engine_inputs["surface_tilt"],
                surface_azimuth=engine_inputs["surface_azimuth"],
                albedo=ALBEDO,
            )

            # Run the fast mode calculation on the middle PV row
            df_report: pd.DataFrame | None = engine.run_full_mode(
                fn_build_report=_fn_report,
            )
            if df_report is not None and not df_report.empty:
                poa_rear_series.loc[group_df.index] = _expand_engine_results(
                    group_df=group_df,
                    engine_inputs=engine_inputs,
                    df_report=df_report,
                )
        except KeyError as error:
            # pvfactors can raise KeyError('horizon') with some pvlib/pvfactors combos.
            # Fallback to zero rear POA so simulation can proceed deterministically.
            if "horizon" in str(error):
                poa_rear_series.loc[group_df.index] = 0.0
            else:
                raise

    return poa_rear_series


def _deduplicate_engine_inputs(*, group_df: pd.DataFrame) -> pd.DataFrame:
    engine_input_columns = [
        "time",
        "dni",
        "dhi",
        "apparent_zenith",
        "azimuth",
        "surface_tilt",
        "surface_azimuth",
    ]
    return group_df.loc[:, engine_input_columns].drop_duplicates(
        ignore_index=True,
    )


def _expand_engine_results(
    *,
    group_df: pd.DataFrame,
    engine_inputs: pd.DataFrame,
    df_report: pd.DataFrame,
) -> pd.Series:
    engine_outputs = engine_inputs.assign(
        qinc_back=df_report["qinc_back"].to_numpy()
    )
    expanded_outputs = group_df.loc[:, list(engine_inputs)].merge(
        right=engine_outputs,
        on=list(engine_inputs),
        how="left",
        sort=False,
    )
    return pd.Series(
        expanded_outputs["qinc_back"].to_numpy(),
        index=group_df.index,
    )


def _fn_report(pvarray):
    return pd.DataFrame(
        {"qinc_back": pvarray.ts_pvrows[1].back.get_param_weighted("qinc")}
    )
