def assign_bandgap_parameters(
    *,
    cec_pv_module: dict,
):
    """Bandgap parameters:
            * WARNING:  CEC Database uses a fixed eg and degdt that
                does not depend on material properties.
            * EgRef: Bandgap at reference conditions in units of [eV]
            * dEgdT:  Temperature dependence of the bandgap at
                    reference condnitions in units of [eV/K]
                    in units of [eV/K]

    Args:
        cec_pv_module: Description for cec_pv_module.
    """
    BANDGAP_PARAMS = {
        "eg": 1.121,
        "degdt": -0.0002677,
    }
    cec_pv_module_with_bandgap_parameters = cec_pv_module | BANDGAP_PARAMS
    return cec_pv_module_with_bandgap_parameters
