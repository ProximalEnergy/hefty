from typing import Any

from app import interfaces


def map_columns_to_proximal_format(
    *,
    cec_pv_module: interfaces.CECPVModuleInterface,
) -> dict[str, Any]:
    """Map CEC PV module fields to Proximal column names.

    Args:
        cec_pv_module: Parsed CEC PV module record.
    """
    column_mapping = {
        "model_number": "model",
        "nameplate_pmax": "pmax",
        "nameplate_isc": "isc",
        "nameplate_voc": "voc",
        "nameplate_ipmax": "imp",
        "nameplate_vpmax": "vmp",
        "alpha_isc": "alpha_isc_relative",
        "beta_voc": "beta_voc_relative",
        "n_s": "cells_in_series",
    }
    cec_pv_module_dict = cec_pv_module.model_dump()
    return {
        column_mapping.get(key, key): value for key, value in cec_pv_module_dict.items()
    }
