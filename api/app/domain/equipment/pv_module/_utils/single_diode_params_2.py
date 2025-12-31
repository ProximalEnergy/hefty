import numpy as np
from pvlib.ivtools.sdm.desoto import _system_of_equations_desoto
from scipy.optimize import minimize


def calc_reference_params(*, pv_module: dict):
    """Calculates the 5 single-diode model parameters using a robust,
        bounded minimization approach.

    Args:
        pv_module: TODO: describe.
    """
    # --- Constants and Module Specs ---
    TEMP_REF_K = 25.0 + 273.15  # Reference temperature in Kelvin
    K_BOLTZMANN_EVK = 8.617333e-05  # Boltzmann constant in eV/K

    TEMP_REF_K = 25.0 + 273.15
    K_BOLTZMANN_EVK = 8.617333e-05

    v_mp = pv_module["vmp"]
    i_mp = pv_module["imp"]
    v_oc = pv_module["voc"]
    i_sc = pv_module["isc"]
    # ... (extract other specs as before) ...
    alpha_sc = pv_module.get("alpha_isc")
    beta_voc = pv_module.get("beta_voc")

    cells_in_series = pv_module["cells_in_series"]
    eg_ref = pv_module.get("eg")
    d_eg_dt = pv_module.get("degdt")

    v_thermal_ref = cells_in_series * K_BOLTZMANN_EVK * TEMP_REF_K

    # --- 1. Get Initial Guesses (Hybrid Approach) ---
    # Try to get r_series from the module, otherwise calculate it
    r_s_guess = pv_module.get("r_series")
    if r_s_guess is None or r_s_guess <= 0:
        r_s_guess = (v_oc - v_mp) / i_mp
        if r_s_guess <= 0:
            r_s_guess = 0.001  # Final fallback

    # Try to get r_shunt from the module, otherwise calculate it
    r_sh_guess = pv_module.get("r_shunt")
    if r_sh_guess is None or r_sh_guess <= 1:  # Shunt resistance must be large
        # Note: This calculation depends on a reasonable r_s_guess
        temp_r_sh = (v_mp - i_mp * r_s_guess) / (i_sc - i_mp) * (v_mp / i_mp)
        if temp_r_sh > 1:
            r_sh_guess = temp_r_sh
        else:
            r_sh_guess = 1000  # Final fallback

    # Get ideality factor or use a default
    a_guess = pv_module.get("diode_ideality_factor", 1.2)

    # Other guesses remain calculated
    i_l_guess = i_sc
    i_o_guess = i_sc / (np.exp(v_oc / (a_guess * v_thermal_ref)) - 1)

    initial_guesses = np.array([i_l_guess, i_o_guess, r_s_guess, r_sh_guess, a_guess])

    # --- 2. Define Objective Function for Minimizer ---
    # The function to be minimized is the sum of squares of the
    # residuals from the De Soto system of equations.
    specs = (
        i_sc,
        v_oc,
        i_mp,
        v_mp,
        beta_voc,
        alpha_sc,
        eg_ref,
        d_eg_dt,
        TEMP_REF_K,
        K_BOLTZMANN_EVK,
    )

    def objective_func(params, specs):  # nosemgrep: python-enforce-keyword-only-args
        """todo

        Args:
            params: TODO: describe.
            specs: TODO: describe.
        """
        residuals = _system_of_equations_desoto(params, specs)
        residuals = np.array(residuals)
        return np.sum(residuals**2)

    # --- 3. Define Physical Bounds for Each Parameter ---
    # (I_L, I_o, R_s, R_sh, a)
    # These bounds prevent the solver from exploring non-physical regions.
    bounds = [
        (0.1 * i_sc, 2.0 * i_sc),  # I_L_ref
        (1e-14, 1e-5),  # I_o_ref (wider range)
        (1e-5, 1.0),  # R_s (wider range)
        (10, 50000),  # R_sh (wider range)
        (0.5, 2.5),  # a_ref (wider range)
    ]

    # --- 4. Run the Bounded Optimization ---
    result = minimize(
        fun=objective_func,
        x0=initial_guesses,
        args=(specs,),
        method="L-BFGS-B",
        bounds=bounds,
        options={"ftol": 1e-10, "gtol": 1e-10},  # Tighter tolerance can help
    )

    if not result.success:
        raise RuntimeError(f"Parameter fitting failed to converge: {result.message}")

    # --- 5. Unpack and Return Results ---
    sdm_params = result.x
    params_renamed = {
        "photocurrent": sdm_params[0],
        "diode_saturation_current": sdm_params[1],
        "r_series": sdm_params[2],
        "r_shunt": sdm_params[3],
        "modified_ideality_factor": sdm_params[4],
    }

    # Merge the newly calculated parameters into the pv_module dictionary
    pv_module.update(params_renamed)
    return pv_module
