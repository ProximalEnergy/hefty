from typing import Any

from app.core.equipment._utils.enumerations import ONDformat
from app.core.equipment.inverter.parse_ond.s01a_read_ond import read_ond
from app.core.equipment.inverter.parse_ond.s01b_read_ond_binary import read_ond_binary
from app.core.equipment.inverter.parse_ond.s02_format_ond import convert_ond_data
from app.core.equipment.inverter.parse_ond.s03_calc_power_dc_nominal import (
    calc_power_dc_nominal,
)
from app.core.equipment.inverter.parse_ond.s04_calc_sandia_fit import calc_fit_sandia
from app.core.equipment.inverter.parse_ond.s05_qc import validate_inverter_config


def parse_ond(
    *,
    file_content: bytes,
) -> dict[str, Any]:
    """
    Parse OND file content and extract inverter information.

    WARNINGS:
        - The Binary Format is not working very well and is not complete

    """

    # Process through the pipeline
    # 1. Read the OND file
    try:
        ond_data = read_ond(file_content=file_content)
        ond_format = ONDformat.TEXT
    except UnicodeDecodeError as e:
        raise ValueError(
            "This may be a PVsyst Binary File from before PVsyst v6."
            "We cannot currently parse these types of files"
        )
        ond_data = read_ond_binary(file_content=file_content)
        ond_format = ONDformat.BINARY

    inverter_data = convert_ond_data(inverter=ond_data, ond_format=ond_format)
    inverter_data = calc_power_dc_nominal(inverter=inverter_data)
    inverter_data = calc_fit_sandia(inverter=inverter_data)
    inverter_data = validate_inverter_config(inverter=inverter_data)

    return inverter_data
