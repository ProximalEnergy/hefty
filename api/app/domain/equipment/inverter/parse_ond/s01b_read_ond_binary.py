from app.domain.equipment._utils.real48_utils import (
    FORWARD_SLASH_MARKER,
    VERTICAL_BAR_MARKER,
    _find_marker_index,
    _get_param_index,
    _read48_to_float,
)


# --- Utility Functions ---
def _extract_eff_curve(
    *, start_idx: int, byte_data: bytes
) -> list[tuple[float, float]]:
    """Extracts the 7 efficiency points for a single curve.
        Each point is a pair of P_in (DC power) and an efficiency-related value.

    Args:
        start_idx: Description for start_idx.
        byte_data: Description for byte_data.
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
    """Parses the entire efficiency section, handling both single and multi-curve files.
        Returns the index of the last byte parsed.

    Args:
        data: Description for data.
        byte_array: Description for byte_array.
        real48_start_index: Description for real48_start_index.
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
    """Parses the final part of the file for remarks and checks for 'Bipolar'.

    Args:
        byte_array: Description for byte_array.
        start_index: Description for start_index.
    """
    remarks_data = {"IsBipolar": False, "RemarksHex": ""}
    if start_index > 0 and start_index < len(byte_array):
        remaining_bytes = byte_array[start_index:]
        remarks_data["RemarksHex"] = remaining_bytes.hex(" ")
        # Check for the ASCII sequence for "Bipolar"
        if b"Bipolar" in remaining_bytes:
            remarks_data["IsBipolar"] = True
    return remarks_data
