import struct
from typing import Any

from app.domain.equipment._utils.real48_utils import (
    DOT_MARKER,
    DOUBLE_DOT_MARKER,
    FORWARD_SLASH_MARKER,
    SEMICOLON_MARKER,
    VERTICAL_BAR_MARKER,
    _find_marker_index,
    _get_param_index,
    _read48_to_float,
)


# --- Utility Functions ---
def _extract_eff_curve(
    *, start_idx: int, byte_data: bytes
) -> list[tuple[float, float]]:
    """
    Extracts the 7 efficiency points for a single curve.
    Each point is a pair of P_in (DC power) and an efficiency-related value.
    """
    curve: list[tuple[float, float]] = []
    if not start_idx or start_idx >= len(byte_data):
        return curve

    for i in range(7):
        pin_idx = _get_param_index(start_index=start_idx, offset_num=i * 5)
        peff_idx = _get_param_index(start_index=start_idx, offset_num=i * 5 + 1)

        if peff_idx + 6 > len(byte_data):
            break  # Avoid reading past the end of the byte array

        p_in_kw_bytes = byte_data[pin_idx : pin_idx + 6]
        p_in_eff_bytes = byte_data[peff_idx : peff_idx + 6]

        p_in_watts = _read48_to_float(real48=p_in_kw_bytes)
        p_in_eff = _read48_to_float(real48=p_in_eff_bytes)

        if p_in_watts > 0:
            # The efficiency is calculated from the two values
            efficiency = 100 * p_in_eff / p_in_watts
            curve.append((p_in_watts, efficiency))
    return curve


def _parse_efficiency_section(
    *,
    data: dict,
    byte_array: bytes,
    real48_start_index: int,
) -> int:
    """
    Parses the entire efficiency section, handling both single and multi-curve files.
    Returns the index of the last byte parsed.
    """
    # This dictionary will hold all efficiency-related data
    eff_data: dict[str, list[tuple[float, float]]] = {
        "StandardEfficiencyCurve": [],
        "LowVoltageEfficiencyCurve": [],
        "MediumVoltageEfficiencyCurve": [],
        "HighVoltageEfficiencyCurve": [],
    }

    # Check for older file format using VERTICAL_BAR_MARKER as the primary separator
    eff_curve_start_index = _find_marker_index(
        marker=VERTICAL_BAR_MARKER, start_index=0, byte_array=byte_array
    )
    is_old_format = eff_curve_start_index > 0

    if is_old_format:
        # --- OLD FORMAT LOGIC ---
        eff_curve_start_index += 34
        eff_data["StandardEfficiencyCurve"] = _extract_eff_curve(
            start_idx=eff_curve_start_index, byte_data=byte_array
        )
        last_parsed_index = eff_curve_start_index
        # Check for more curves by looking for the next marker
        is_multi_curved = (
            _find_marker_index(
                marker=VERTICAL_BAR_MARKER,
                start_index=eff_curve_start_index,
                byte_array=byte_array,
            )
            > 0
        )

    else:
        # --- NEW FORMAT LOGIC ---
        eff_curve_start_index = _find_marker_index(
            marker=FORWARD_SLASH_MARKER,
            start_index=real48_start_index + 108,
            byte_array=byte_array,
        )
        if not eff_curve_start_index:
            return 0
        eff_curve_start_index += 44
        eff_data["StandardEfficiencyCurve"] = _extract_eff_curve(
            start_idx=eff_curve_start_index, byte_data=byte_array
        )
        last_parsed_index = eff_curve_start_index
        # Multi-curve files are typically larger
        is_multi_curved = len(byte_array) > 1024

    # --- MULTI-CURVE PARSING (applies to both formats, just markers differ) ---
    if is_multi_curved:
        eff_attribute_start_index = _find_marker_index(
            marker=FORWARD_SLASH_MARKER,
            start_index=last_parsed_index + 240,
            byte_array=byte_array,
        )
        if not eff_attribute_start_index:
            return last_parsed_index  # Stop if attributes not found
        eff_attribute_start_index += 2

        # Extract attributes for the other curves (voltages, efficiencies)
        attr_map = {
            "LowVoltageLevel": 0,
            "MediumVoltageLevel": 1,
            "HighVoltageLevel": 2,
            "LowVEfficMax": 3,
            "MediumVEfficMax": 4,
            "HighVEfficMax": 5,
            "LowVEfficEuro": 6,
            "MediumVEfficEuro": 7,
            "HighVEfficEuro": 8,
        }
        for name, offset in attr_map.items():
            start = _get_param_index(
                start_index=eff_attribute_start_index, offset_num=offset
            )
            data[name] = _read48_to_float(real48=byte_array[start : start + 6])

        # Sequentially parse the Low, Medium, and High efficiency curves
        marker = VERTICAL_BAR_MARKER if is_old_format else FORWARD_SLASH_MARKER
        offset = 34 if is_old_format else 44

        # Low Voltage Curve
        next_curve_start = _find_marker_index(
            marker=marker, start_index=eff_attribute_start_index, byte_array=byte_array
        )
        if next_curve_start:
            next_curve_start += offset
            eff_data["LowVoltageEfficiencyCurve"] = _extract_eff_curve(
                start_idx=next_curve_start, byte_data=byte_array
            )
            last_parsed_index = next_curve_start

        # Medium Voltage Curve
        next_curve_start = _find_marker_index(
            marker=marker, start_index=last_parsed_index, byte_array=byte_array
        )
        if next_curve_start:
            next_curve_start += offset
            eff_data["MediumVoltageEfficiencyCurve"] = _extract_eff_curve(
                start_idx=next_curve_start, byte_data=byte_array
            )
            last_parsed_index = next_curve_start

        # High Voltage Curve
        next_curve_start = _find_marker_index(
            marker=marker, start_index=last_parsed_index, byte_array=byte_array
        )
        if next_curve_start:
            next_curve_start += offset
            eff_data["HighVoltageEfficiencyCurve"] = _extract_eff_curve(
                start_idx=next_curve_start, byte_data=byte_array
            )
            last_parsed_index = next_curve_start

    data.update(eff_data)
    return last_parsed_index


def _parse_remarks(*, byte_array: bytes, start_index: int) -> dict:
    """Parses the final part of the file for remarks and checks for 'Bipolar'."""
    remarks_data = {"IsBipolar": False, "RemarksHex": ""}
    if start_index > 0 and start_index < len(byte_array):
        remaining_bytes = byte_array[start_index:]
        remarks_data["RemarksHex"] = remaining_bytes.hex(" ")
        # Check for the ASCII sequence for "Bipolar"
        if b"Bipolar" in remaining_bytes:
            remarks_data["IsBipolar"] = True
    return remarks_data


def read_ond_binary(*, file_content: bytes) -> dict:
    """
    Parses a binary .OND file and returns its contents as a dictionary.
    This is a full translation of the VBA logic, handling multiple file formats.
    """
    data: dict[str, Any] = {}
    byte_array = file_content
    if not byte_array:
        return {"error": "File is empty"}

    try:
        # --- 1. Find start indices for metadata strings ---
        manu_start_index = byte_array.find(SEMICOLON_MARKER) + 1
        inv_start_index = byte_array.find(DOT_MARKER) + 1
        source_start_index = _find_marker_index(
            marker=DOT_MARKER, start_index=inv_start_index, byte_array=byte_array
        )
        version_start_index = _find_marker_index(
            marker=DOUBLE_DOT_MARKER,
            start_index=source_start_index,
            byte_array=byte_array,
        )
        version_end_index = _find_marker_index(
            marker=SEMICOLON_MARKER,
            start_index=version_start_index,
            byte_array=byte_array,
        )
        year_start_index = _find_marker_index(
            marker=SEMICOLON_MARKER,
            start_index=version_end_index + 1,
            byte_array=byte_array,
        )

        # --- 2. Find start of the main numerical data block (Real48 encoded) ---
        real48_start_index = (
            _find_marker_index(
                marker=FORWARD_SLASH_MARKER,
                start_index=year_start_index,
                byte_array=byte_array,
            )
            + 6
        )

        # --- 3. Extract string parameters ---
        data["Manufacturer"] = (
            byte_array[manu_start_index : inv_start_index - 1].decode("latin-1").strip()
        )
        data["Model"] = (
            byte_array[inv_start_index : source_start_index - 1]
            .decode("latin-1")
            .strip()
        )
        data["Source"] = (
            byte_array[source_start_index : version_start_index - 4]
            .decode("latin-1")
            .strip()
        )
        data["Version"] = (
            byte_array[version_start_index : version_end_index - 2]
            .decode("latin-1")
            .replace("Version", "User_Added")
            .strip()
        )
        data["Year"] = (
            byte_array[year_start_index : year_start_index + 4]
            .decode("latin-1")
            .strip()
        )

        # --- 4. Get Operation and Phase Type ---
        data["Operation"] = (
            "MPPT" if byte_array[real48_start_index - 4] == 1 else "Fixed Voltage"
        )
        phase_map = {1: "Mono", 2: "Tri", 3: "Bi"}
        data["PhaseType"] = phase_map.get(byte_array[real48_start_index - 1], "Unknown")

        # --- 5. Parse main Real48 encoded parameters ---
        param_map = {
            "PNomAC": 0,
            "VOutConv": 1,
            "VMppMin": 2,
            "VMPPMax": 3,
            "VAbsMax": 4,
            "PSeuil": 5,
            "PMaxOUT": 6,
            "EfficMax": 7,
            "EfficEuro": 8,
            "INomDC": 10,
            "VmppNom": 11,
            "MinV": 12,
            "PNomDC": 13,
            "PMaxDC": 14,
            "IMaxDC": 15,
            "INomAC": 16,
            "IMaxAC": 17,
            "FResNorm": 18,
        }
        for name, offset in param_map.items():
            start = _get_param_index(start_index=real48_start_index, offset_num=offset)
            data[name] = _read48_to_float(real48=byte_array[start : start + 6])

        # --- 6. Parse the complex efficiency section ---
        last_parsed_index = _parse_efficiency_section(
            data=data, byte_array=byte_array, real48_start_index=real48_start_index
        )

        # --- 7. Parse final remarks and check for bipolar inputs ---
        remarks_info = _parse_remarks(
            byte_array=byte_array, start_index=last_parsed_index
        )
        data.update(remarks_info)

    except (IndexError, TypeError, ValueError, struct.error) as e:
        return {"error": f"Failed to parse binary OND file: {e}"}

    return data
