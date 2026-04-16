"""Deprecated local wrapper around pvlib's De Soto fitter.

This module exists only to support the legacy CEC PV-module adaptation path.
Prefer newer parsing and parameter-derivation flows for any new work.
"""

import numpy as np
from pvlib.ivtools.sdm.desoto import _system_of_equations_desoto
from scipy import constants, optimize


def fit_desoto(
    *,
    v_mp,
    i_mp,
    v_oc,
    i_sc,
    alpha_sc,
    beta_voc,
    EgRef=1.121,
    dEgdT=-0.0002677,
    temp_ref=25,
    irrad_ref=1000,
    init_guess=None,
    root_kwargs=None,
):
    """Deprecated Proximal wrapper around pvlib's De Soto fitting routine.

    The only behavior difference from pvlib is that this returns the raw
    ``scipy.optimize.root`` result whether or not the solve succeeds.

    Args:
        v_mp: Voltage at maximum power point.
        i_mp: Current at maximum power point.
        v_oc: Open-circuit voltage.
        i_sc: Short-circuit current.
        alpha_sc: Temperature coefficient for short-circuit current.
        beta_voc: Temperature coefficient for open-circuit voltage.
        EgRef: Bandgap energy at reference conditions.
        dEgdT: Temperature dependence of bandgap energy.
        temp_ref: Reference cell temperature in Celsius.
        irrad_ref: Reference irradiance in W/m^2.
        init_guess: Optional initial guesses for solver parameters.
        root_kwargs: Additional kwargs passed to ``scipy.optimize.root``.
    """
    k = constants.value("Boltzmann constant in eV/K")
    t_ref = temp_ref + 273.15

    init_guess_keys = ["IL_0", "Io_0", "Rs_0", "Rsh_0", "a_0"]
    init_guess = init_guess or {}
    root_kwargs = root_kwargs or {}
    init = {key: None for key in init_guess_keys}
    for key in init_guess:
        if key in init_guess_keys:
            init[key] = init_guess[key]
        else:
            raise ValueError(
                f"'{key}' is not a valid name; allowed values are {init_guess_keys}"
            )

    params_i = np.array([init[k] for k in init_guess_keys])
    specs = (
        i_sc,
        v_oc,
        i_mp,
        v_mp,
        beta_voc,
        alpha_sc,
        EgRef,
        dEgdT,
        t_ref,
        k,
    )

    optimize_result = optimize.root(
        _system_of_equations_desoto,
        x0=params_i,
        args=(specs,),
        **root_kwargs,
    )
    sdm_params = optimize_result.x

    return (
        {
            "I_L_ref": sdm_params[0],
            "I_o_ref": sdm_params[1],
            "R_s": sdm_params[2],
            "R_sh_ref": sdm_params[3],
            "a_ref": sdm_params[4],
            "alpha_sc": alpha_sc,
            "EgRef": EgRef,
            "dEgdT": dEgdT,
            "irrad_ref": irrad_ref,
            "temp_ref": temp_ref,
        },
        optimize_result,
    )
