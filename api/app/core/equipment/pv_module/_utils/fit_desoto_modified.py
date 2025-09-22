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
    cells_in_series,
    EgRef=1.121,
    dEgdT=-0.0002677,
    temp_ref=25,
    irrad_ref=1000,
    init_guess={},
    root_kwargs={},
):
    """
    This is a Proximal modified version of the fit_desoto function in pvlib.
    The main difference is that it exports the results of the scipy.optimize.root
    function whether or not the solve is successful.
    """
    # Constants
    k = constants.value("Boltzmann constant in eV/K")  # in eV/K
    Tref = temp_ref + 273.15  # [K]

    # initial guesses of variables for computing convergence:
    # Default values are taken from [1], p753
    init_guess_keys = ["IL_0", "Io_0", "Rs_0", "Rsh_0", "a_0"]  # order matters
    init = {key: None for key in init_guess_keys}
    # overwrite if optional init_guess is provided
    for key in init_guess:
        if key in init_guess_keys:
            init[key] = init_guess[key]
        else:
            raise ValueError(
                f"'{key}' is not a valid name; allowed values are {init_guess_keys}"
            )
    # params_i : initial values vector
    params_i = np.array([init[k] for k in init_guess_keys])

    # specs of module
    specs = (i_sc, v_oc, i_mp, v_mp, beta_voc, alpha_sc, EgRef, dEgdT, Tref, k)

    # computing with system of equations described in [1]
    optimize_result = optimize.root(
        _system_of_equations_desoto, x0=params_i, args=(specs,), **root_kwargs
    )

    sdm_params = optimize_result.x

    # results
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
