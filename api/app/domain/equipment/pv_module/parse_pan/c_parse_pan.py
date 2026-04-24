from typing import Any

from app.domain.equipment._utils.enumerations import PANformat
from app.domain.equipment.pv_module.parse_pan.s01a_read_pan import read_pan_txt
from app.domain.equipment.pv_module.parse_pan.s01b_read_pan_binary import (
    read_pan_binary,
)
from app.domain.equipment.pv_module.parse_pan.s02_column_mapping import (
    format_pan_to_pvmodule,
)
from app.domain.equipment.pv_module.parse_pan.s03_bandgap_parameters import (
    assign_bandgap_parameters,
)
from app.domain.equipment.pv_module.parse_pan.s04_absolute_temp_coefficients import (
    calc_absolute_temp_coefficients,
)
from app.domain.equipment.pv_module.parse_pan.s05_single_diode_params import (
    solve_stc_parameters,
)


def parse_pan(*, file_content: bytes) -> dict[str, Any]:
    """Parse PAN file content and extract PV module information.

        Possible Improvements:
            - PAN files come with Rseries, Rshunt parameters etc.
              We should use them in our initial guess

    Args:
        file_content: Description for file_content.
    """
    try:
        pan_format = PANformat.TEXT
        pan_data = read_pan_txt(file_content=file_content)
    except UnicodeDecodeError:
        pan_format = PANformat.BINARY
        pan_data = read_pan_binary(file_content=file_content)

    pv_module_data = format_pan_to_pvmodule(
        pan_data=pan_data,
        pan_format=pan_format,
    )
    pv_module_data = assign_bandgap_parameters(
        pv_module=pv_module_data,
    )
    pv_module_data = calc_absolute_temp_coefficients(
        pv_module=pv_module_data,
    )
    pv_module_data = solve_stc_parameters(
        pv_module_data=pv_module_data,
    )

    return dict(pv_module_data)
