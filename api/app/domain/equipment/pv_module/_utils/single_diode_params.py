"""Deprecated legacy single-diode helper for CEC PV-module adaptation.

This module was restored to keep the existing CEC conversion path working.
Do not add new callers; migrate existing usage when a replacement is ready.
"""

import warnings

import numpy as np
from app.domain.equipment.pv_module._utils.fit_desoto_modified import (
    fit_desoto,
)


def calc_reference_params(
    *,
    pv_module: dict,
):
    """Deprecated single-diode parameter derivation for legacy CEC imports.

    Calculates:
    - series resistance
    - shunt resistance
    - diode ideality factor
    - photocurrent
    - diode saturation current

    The solve is iterative because the single-diode parameters are derived from
    nameplate and temperature-coefficient inputs rather than read directly.

    Args:
        pv_module: Module dictionary containing the needed electrical inputs.
    """
    warnings.warn(
        "calc_reference_params is deprecated and kept only for legacy CEC "
        "PV-module adaptation. Prefer newer parameter derivation paths.",
        DeprecationWarning,
        stacklevel=2,
    )

    temp_ref = 25.0
    irrad_ref = 1000.0
    k_boltzmann = 8.617333262145179e-05

    v_mp = pv_module["vmp"]
    i_mp = pv_module["imp"]
    v_oc = pv_module["voc"]
    i_sc = pv_module["isc"]
    cells_in_series = pv_module["cells_in_series"]

    series_resistance_guess = pv_module.get("r_series")
    if not series_resistance_guess:
        fill_factor_guess = (v_mp * i_mp) / (v_oc * i_sc)
        series_resistance_guess = (v_oc - v_mp) / i_mp * (1 - fill_factor_guess)

    shunt_resistance_guess = pv_module.get("r_shunt")
    if not shunt_resistance_guess:
        di_dv_approx = (i_mp - i_sc) / v_mp
        shunt_resistance_guess = -1 / di_dv_approx

    thermal_voltage = 0.0257

    a_0_guess = pv_module.get("diode_ideality_factor")
    if not a_0_guess:
        a_0_guess = 1.5 * k_boltzmann * temp_ref * cells_in_series

    i_0_guess = i_sc / (
        np.exp(v_oc / (a_0_guess * cells_in_series * thermal_voltage)) - 1
    )

    original_init_guess = {
        "Rs_0": series_resistance_guess,
        "Rsh_0": shunt_resistance_guess,
        "a_0": a_0_guess,
        "IL_0": i_sc,
        "Io_0": i_0_guess,
    }
    init_guess = original_init_guess.copy()

    counter = 0
    fit_is_successful = False
    params = {}
    while fit_is_successful is False:
        counter += 1
        params, optimization_results = fit_desoto(
            v_mp=pv_module.get("vmp"),
            i_mp=pv_module.get("imp"),
            v_oc=pv_module.get("voc"),
            i_sc=pv_module.get("isc"),
            alpha_sc=pv_module.get("alpha_isc"),
            beta_voc=pv_module.get("beta_voc"),
            EgRef=pv_module.get("eg"),
            dEgdT=pv_module.get("degdt"),
            temp_ref=temp_ref,
            irrad_ref=irrad_ref,
            init_guess=init_guess,
        )
        fit_is_successful = optimization_results.success

        if params["R_s"] < 0:
            params["R_s"] = original_init_guess["Rs_0"]
        if params["R_sh_ref"] < 0:
            params["R_sh_ref"] = original_init_guess["Rsh_0"]
        if params["I_L_ref"] > pv_module["isc"]:
            params["I_L_ref"] = pv_module["isc"]
        if params["I_o_ref"] < 0:
            params["I_o_ref"] = i_0_guess

        init_guess = {
            "Rs_0": params["R_s"],
            "Rsh_0": params["R_sh_ref"],
            "a_0": params["a_ref"],
            "IL_0": params["I_L_ref"],
            "Io_0": params["I_o_ref"],
        }

        if counter == 5000:
            params_renamed = {
                "photocurrent": params["I_L_ref"],
                "diode_saturation_current": params["I_o_ref"],
                "r_series": params["R_s"],
                "r_shunt": params["R_sh_ref"],
                "modified_ideality_factor": params["a_ref"],
            }
            raise ValueError(
                "Maximum number of iterations reached. "
                f"Current parameters: {params_renamed}"
            )

    params_renamed = {
        "photocurrent": params["I_L_ref"],
        "diode_saturation_current": params["I_o_ref"],
        "r_series": params["R_s"],
        "r_shunt": params["R_sh_ref"],
        "modified_ideality_factor": params["a_ref"],
    }
    return pv_module | params_renamed
