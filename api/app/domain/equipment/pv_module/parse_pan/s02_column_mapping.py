from typing import Any

from app.domain.equipment._utils.enumerations import PANformat


def format_pan_to_pvmodule(
    *,
    pan_data: dict[str, Any],
    pan_format: PANformat,
) -> dict[str, Any]:
    """
    Formats the parsed PAN file data into the structure of the PVModule model.

    WARNINGS:
        - Binary PAN files sets length and width to -999.9

    """
    match pan_format:
        case PANformat.TEXT:
            # Flatten commercial section to top level
            pan_data = pan_data["PVObject_"]
            pan_data.update(pan_data.pop("PVObject_Commercial", {}))

            # Output field mapping with type hints
            output_mapping = {
                "manufacturer": ("Manufacturer", str),
                "model": ("Model", str),
                "technology": ("Technol", str),
                "pmax": ("PNom", float),
                "isc": ("Isc", float),
                "voc": ("Voc", float),
                "imp": ("Imp", float),
                "vmp": ("Vmp", float),
                "cells_in_series": ("NCelS", int),
                "cells_in_parallel": ("NCelP", int),
                "r_series": ("RSerie", float),
                "r_shunt": ("RShunt", float),
                "diode_ideality_factor": ("Gamma", float),
                "alpha_isc": ("muISC", float),
                "beta_voc": ("muVocSpec", float),
                "gamma_pmax": ("muPmpReq", float),
                "width": ("Width", float),
                "length": ("Height", float),
                "bifaciality_factor": ("BifacialityFactor", float),
            }
        case PANformat.BINARY:
            pan_data["length"] = -999.9
            pan_data["width"] = -999.9
            output_mapping = {
                "manufacturer": ("Manufacturer", str),
                "model": ("Model", str),
                "technology": ("Technology", str),
                "length": ("length", float),
                "width": ("width", float),
                "cells_in_series": ("Cells_In_Series", int),
                "cells_in_parallel": ("Cells_In_Parallel", int),
                "pmax": ("PNom", float),
                "isc": ("Isc", float),
                "voc": ("Voc", float),
                "imp": ("Imp", float),
                "vmp": ("Vmp", float),
                "r_series": ("RSerie", float),
                "r_shunt": ("RShunt", float),
                "gamma_pmax": ("muPmp", float),
                "alpha_isc": ("muISC", float),
                "beta_voc": ("muVocSpec", float),
            }

    # Build the formatted data dictionary
    formatted_data = {}
    for output_key, (pan_key, target_type) in output_mapping.items():
        if pan_key in pan_data:
            formatted_data[output_key] = target_type(pan_data[pan_key])
        elif output_key == "bifaciality_factor":
            formatted_data[output_key] = 0.0
        else:
            formatted_data[output_key] = target_type(pan_data[pan_key])

    return formatted_data
