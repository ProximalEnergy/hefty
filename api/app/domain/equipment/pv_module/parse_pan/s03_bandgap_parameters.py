def assign_bandgap_parameters_pan(
    *,
    pv_module: dict,
):
    """Bandgap parameters:
            * WARNING:  CEC Database uses a fixed eg and degdt that
                does not depend on material properties.
            * EgRef: Bandgap at reference conditions in units of [eV]
            * dEgdT:  Temperature dependence of the bandgap at
                    reference condnitions in units of [eV/K]
                    in units of [eV/K]

    Args:
        pv_module: Description for pv_module.
    """
    # --- Switch Statement ---
    if "Si" in pv_module["technology"]:
        pv_module["technology"] = "c-Si"
        BANDGAP_PARAMS = {
            "eg": 1.121,
            "degdt": -0.0002677,
        }
    elif "CdTe" in pv_module["technology"]:
        pv_module["technology"] = "CdTe"
        BANDGAP_PARAMS = {
            "eg": 1.475,
            "degdt": -0.0003,
        }
    else:
        raise ValueError("Unknown module technology aka Technol in PAN file")

    # --- Dictionary Union ---
    pv_module = pv_module | BANDGAP_PARAMS

    # --- Return Statement ---
    return pv_module
