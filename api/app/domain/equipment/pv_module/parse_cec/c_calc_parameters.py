from typing import Any

from app import interfaces
from app.domain.equipment.pv_module._utils.single_diode_params import (
    calc_reference_params,
)
from app.domain.equipment.pv_module.parse_cec.s00_column_mapping import (
    map_columns_to_proximal_format,
)
from app.domain.equipment.pv_module.parse_cec.s01_bandgap_parameters import (
    assign_bandgap_parameters_cec,
)
from app.domain.equipment.pv_module.parse_cec.s02_absolute_temp_coefficients import (
    calc_absolute_temp_coefficients,
)


def adapt_cec_pv_module_to_proximal(
    *,
    cec_pv_module: interfaces.CECPVModule,
) -> interfaces.PVModule | dict:
    """todo

    Args:
        cec_pv_module: Description for cec_pv_module.
    """
    adapted_cec_pv_module = map_columns_to_proximal_format(cec_pv_module=cec_pv_module)
    adapted_cec_pv_module = assign_bandgap_parameters_cec(
        cec_pv_module=adapted_cec_pv_module,
    )
    adapted_cec_pv_module = calc_absolute_temp_coefficients(
        cec_pv_module=adapted_cec_pv_module,
    )
    adapted_cec_pv_module = calc_reference_params(
        pv_module=adapted_cec_pv_module,
    )
    # Type assertion to satisfy mypy
    result: interfaces.PVModule | dict[Any, Any] = adapted_cec_pv_module
    return result
