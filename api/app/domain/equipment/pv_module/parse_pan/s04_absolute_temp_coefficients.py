"""
PVsyst PAN files store:
    - muIsc:  Temperature Coeff (Isc) in mA/°C
    - muVoc:  Temperature Coeff (Voc) in mV/°C
              In percentage (relative) format
"""


def calc_absolute_temp_coefficients(
    *,
    pv_module: dict,
) -> dict:
    """
    Calculate the absolute temperature coefficients for a PV module
    by converting units to A and V
    """

    pv_module["alpha_isc"] = pv_module["alpha_isc"] * 1e-3
    pv_module["beta_voc"] = pv_module["beta_voc"] * 1e-3

    return pv_module
