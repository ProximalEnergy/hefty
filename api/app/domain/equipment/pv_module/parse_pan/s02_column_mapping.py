from typing import Any

from app.domain.equipment._utils.enumerations import PANformat


def _get_first_value(
    *,
    data: dict[str, Any],
    keys: tuple[str, ...],
    output_key: str,
) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    raise ValueError(f"Something unexpected happened while mapping {output_key}")


def format_pan_to_pvmodule(
    *,
    pan_data: dict[str, Any],
    pan_format: PANformat,
) -> dict[str, Any]:
    """
    Format parsed PAN file data into a dictionary structure matching the PVModule model.

    Converts field names and types from a parsed PAN file (either text or binary
    format) into a standard dictionary suitable for PVModule ingestion.
    Handles differences between text and binary PAN formats, including missing
    or placeholder values.

    Args:
        pan_data (dict[str, Any]): The raw, already-parsed data from a PAN file.
            Should come from a prior parsing step and may contain nested structures.
        pan_format (PANformat): Enum value indicating the source PAN file format.
            Determines which mapping and structure to use for extraction.
            - PANformat.TEXT expects 'PVObject_' as the top-level key and
              flattens 'PVObject_Commercial' sub-fields.
            - PANformat.BINARY assumes a flat structure and sets 'length' and
              'width' fields to -999.9 as placeholders.

    Returns:
        dict[str, Any]: Dictionary containing all expected PVModule fields with
        type-consistent values, ready for model insertion or serialization.

    Note:
        - For missing fields 'bifaciality_factor' and 'beta_voc', sets default 0.0.
        - For binary files, 'length' and 'width' will be -999.9 (invalid).
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
                "r_shunt_0": (("RShunt0", "RShunt_0", "Rp_0"), float),
                "r_shunt_exponent": (
                    ("RShuntExp", "RShunt_exp", "Rp_Exp"),
                    float,
                ),
                "diode_ideality_factor": ("Gamma", float),
                "diode_ideality_factor_temp_coefficient": (
                    ("muGamma", "MuGamma"),
                    float,
                ),
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
                "r_shunt_0": ("RShunt_0", float),
                "r_shunt_exponent": ("RShunt_exp", float),
                "diode_ideality_factor": ("Gamma", float),
                "diode_ideality_factor_temp_coefficient": ("muGamma", float),
                "gamma_pmax": ("muPmp", float),
                "alpha_isc": ("muISC", float),
                "beta_voc": ("muVocSpec", float),
            }

    # Build the formatted data dictionary
    formatted_data = {}
    for output_key, (pan_key, target_type) in output_mapping.items():
        if isinstance(pan_key, tuple):
            formatted_data[output_key] = target_type(
                _get_first_value(
                    data=pan_data,
                    keys=pan_key,
                    output_key=output_key,
                )
            )
        elif isinstance(pan_key, str) and pan_key in pan_data:
            formatted_data[output_key] = target_type(pan_data[pan_key])
        elif output_key == "bifaciality_factor":
            formatted_data[output_key] = 0.0
        elif output_key == "beta_voc":
            # Estimate beta_voc from technology when muVocSpec is missing
            technology = formatted_data.get("technology", "").lower()
            voc = formatted_data.get("voc", 0.0)
            if "cdte" in technology:
                # CdTe modules: beta_voc = -0.0028 × Voc
                formatted_data[output_key] = -0.0028 * voc
            else:
                # Crystalline silicon (default): beta_voc = -0.0029 × Voc
                formatted_data[output_key] = -0.0029 * voc
        elif output_key == "r_shunt_0":
            formatted_data[output_key] = formatted_data["r_shunt"]
        elif output_key == "r_shunt_exponent":
            formatted_data[output_key] = 5.5
        elif output_key == "diode_ideality_factor":
            formatted_data[output_key] = 1.2
        elif output_key == "diode_ideality_factor_temp_coefficient":
            formatted_data[output_key] = 0.0
        else:
            raise ValueError(
                f"Something unexpected happened while mapping {output_key}"
            )

    return formatted_data
