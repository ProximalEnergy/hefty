import numpy as np
from app.core.equipment.pv_module._utils.fit_desoto_modified import fit_desoto


def calc_reference_params(
    *,
    pv_module: dict,
):
    """
    Calculate Single Diode Parameters:
        - Series resistance
        - Shunt resistance
        - Diode ideality factor
        - Photocurrent
        - Diode saturation current

    The calculation is done via an iterative process since only
    PAN parameters are known.  We are solving for the
    these parameters at STC.

    Possible Improvements:
        - Check the residuals to see if they are improving on each iteration
        - Add alternative initial guesses
        - Add a guess for the diode ideality factor
        - Add a guess for the diode saturation current

    More information:
        - https://github.com/pvlib/pvlib-python/issues/2425
        - https://www.osti.gov/pages/biblio/2550692


    """

    # --- Constants ---
    TEMP_REF = 25.0
    IRRAD_REF = 1000.0
    K = 8.617333262145179e-05  # eV/K

    # --- Variables ---
    v_mp = pv_module["vmp"]
    i_mp = pv_module["imp"]
    v_oc = pv_module["voc"]
    i_sc = pv_module["isc"]
    cells_in_series = pv_module["cells_in_series"]
    technology = pv_module["technology"]

    # # --- Calculation of an Initial Guess ---
    # Series Resistance
    series_resistance_guess = pv_module.get("r_series")
    if not series_resistance_guess:
        fill_factor_guess = (v_mp * i_mp) / (v_oc * i_sc)
        series_resistance_guess = (v_oc - v_mp) / i_mp * (1 - fill_factor_guess)

    # Shunt resistance is the negative reciprocal of the slope
    shunt_resistance_guess = pv_module.get("r_shunt")
    if not shunt_resistance_guess:
        dI_dV_approx = (i_mp - i_sc) / (v_mp - 0)
        shunt_resistance_guess = -1 / dI_dV_approx

    # # Estimate ideality factor
    thermal_voltage = 0.0257  # V at 25°C

    a_0_guess = pv_module.get("diode_ideality_factor")
    if not a_0_guess:
        a_0_guess = 1.5 * K * TEMP_REF * cells_in_series

    # Estimate diode saturation current
    i_0_guess = i_sc / (
        np.exp(v_oc / (a_0_guess * cells_in_series * thermal_voltage)) - 1
    )

    original_init_guess = {
        "Rs_0": series_resistance_guess,  # series resistance
        "Rsh_0": shunt_resistance_guess,  # shunt resistance
        "a_0": a_0_guess,  # diode ideality factor
        "IL_0": i_sc,  # photocurrent
        "Io_0": i_0_guess,  # diode saturation current
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
            cells_in_series=pv_module.get("cells_in_series"),  # type: ignore
            EgRef=pv_module.get("eg"),  # type: ignore
            dEgdT=pv_module.get("degdt"),  # type: ignore
            temp_ref=TEMP_REF,  # type: ignore
            irrad_ref=IRRAD_REF,  # type: ignore
            init_guess=init_guess,
        )
        fit_is_successful = optimization_results.success

        # --- Re-adjust non-physical parameters ---
        if params["R_s"] < 0:
            params["R_s"] = original_init_guess["Rs_0"]
        if params["R_sh_ref"] < 0:
            params["R_sh_ref"] = original_init_guess["Rsh_0"]
        if params["I_L_ref"] > pv_module["isc"]:
            params["I_L_ref"] = pv_module["isc"]
        if params["I_o_ref"] < 0:
            params["I_o_ref"] = i_0_guess

        init_guess = {
            "Rs_0": params["R_s"],  # series resistance
            "Rsh_0": params["R_sh_ref"],  # shunt resistance
            "a_0": params["a_ref"],  # diode ideality factor
            "IL_0": params["I_L_ref"],  # photocurrent
            "Io_0": params["I_o_ref"],  # diode saturation current
        }

        # if counter == 100:
        #     match technology:
        #         case "c-Si":
        #             params["a_0"] = 1.5
        #         case "CdTe":
        #             params["a_0"] = 8.0
        # elif counter == 200:
        #     match technology:
        #         case "c-Si":
        #             params["a_0"] = 0.3
        #         case "CdTe":
        #             params["a_0"] = 8.0

        if counter == 5000:
            # Convert params dictionary to a new dictionary with renamed keys
            params_renamed = {
                "photocurrent": params["I_L_ref"],
                "diode_saturation_current": params["I_o_ref"],
                "r_series": params["R_s"],
                "r_shunt": params["R_sh_ref"],
                "modified_ideality_factor": params["a_ref"],
            }

            raise ValueError(f"""
                Maximum number of iterations reached.
                Current parameters: {params_renamed}
                """)

    # Convert params dictionary to a new dictionary with renamed keys
    params_renamed = {
        "photocurrent": params["I_L_ref"],  # type-ignore
        "diode_saturation_current": params["I_o_ref"],
        "r_series": params["R_s"],
        "r_shunt": params["R_sh_ref"],
        "modified_ideality_factor": params["a_ref"],
    }

    # replace with manual inputs
    pv_module = pv_module | params_renamed

    return pv_module
