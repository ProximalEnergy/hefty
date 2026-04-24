import math
from typing import Any

from app.domain.equipment._utils.enumerations import PANformat

# A unique sentinel to represent a missing value
MISSING = object()


def format_pan_to_pvmodule(
    *,
    pan_data: dict[str, Any],
    pan_format: PANformat,
) -> dict[str, Any]:
    """
    Format PAN data into a PV module dictionary.

    Args:
        pan_data: The raw PAN data dictionary.
        pan_format: The format of the PAN data.

    Returns:
        A dictionary containing the mapped PV module data.
    """
    # 1. Normalize the input source
    source = pan_data.copy()
    if pan_format == PANformat.TEXT:
        source.update(source.get("PVObject_", {}))
        source.update(source.pop("PVObject_Commercial", {}))
    else:
        # Binary specific placeholders per original requirements
        source["length"] = -999.9
        source["width"] = -999.9

    # 2. Define the exact keys to look for
    # Format: "output_key": (possible_source_keys_tuple, target_type)
    mapping = {
        "manufacturer": (("Manufacturer",), str),
        "model": (("Model",), str),
        "technology": (("Technol", "Technology"), str),
        "pmax": (("PNom",), float),
        "isc": (("Isc",), float),
        "voc": (("Voc",), float),
        "imp": (("Imp",), float),
        "vmp": (("Vmp",), float),
        "cells_in_series": (("NCelS", "Cells_In_Series"), int),
        "cells_in_parallel": (("NCelP", "Cells_In_Parallel"), int),
        "r_series": (("RSerie",), float),
        "r_shunt": (("RShunt",), float),
        "r_shunt_0": (("RShunt0", "RShunt_0", "Rp_0"), float),
        "r_shunt_exponent": (("RShuntExp", "RShunt_exp", "Rp_Exp"), float),
        "diode_ideality_factor": (("Gamma",), float),
        "diode_ideality_factor_temp_coefficient": (("muGamma", "MuGamma"), float),
        "alpha_isc": (("muISC",), float),
        "beta_voc": (("muVocSpec",), float),
        "gamma_pmax": (("muPmpReq", "muPmp"), float),
        "width": (("Width", "width"), float),
        "length": (("Height", "length"), float),
        "bifaciality_factor": (("BifacialityFactor",), float),
        "d2mutau": (("D2MuTau",), float),
    }

    formatted: dict[str, Any] = {}

    for out_key, (src_keys, target_type) in mapping.items():
        # 1. Search for the value
        raw_val = next((source[k] for k in src_keys if k in source), MISSING)

        if raw_val is not MISSING:
            # 2. Convert raw_val to the target_type (int, float, or str)
            formatted[out_key] = target_type(raw_val)
            continue

        # --- Strict Fallback Logic (Only for specific fields) ---
        if out_key == "bifaciality_factor":
            formatted[out_key] = 0.0
        elif out_key == "beta_voc":
            tech = formatted.get("technology", "").lower()
            voc = formatted.get("voc", 0.0)
            coeff = -0.0028 if "cdte" in tech else -0.0029
            formatted[out_key] = coeff * voc
        elif out_key == "r_shunt_0":
            formatted[out_key] = formatted["r_shunt"]
        elif out_key == "r_shunt_exponent":
            formatted[out_key] = 5.5
        elif out_key == "diode_ideality_factor":
            formatted[out_key] = 1.2
        elif out_key == "diode_ideality_factor_temp_coefficient":
            formatted[out_key] = 0.0
        elif out_key == "d2mutau":
            if "cdte" not in formatted.get("technology", "").lower():
                formatted[out_key] = math.nan
            else:
                raise ValueError("Missing required parameter: D2MuTau")
        else:
            # If it's not a special case and wasn't found, fail explicitly
            raise ValueError(f"Something unexpected happened while mapping {out_key}")

    return formatted
