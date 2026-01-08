"""
Older versions of PAN files created by PVsyst use a Borland Pascal Real48 format.

This is based on:
    https://github.com/CanadianSolar/CASSYS/blob/
    b5487bb4e9e77174c805d64e3c960c46d357b7e2/CASSYS%20Interface/
    DatabaseImportModule.vba#L4
"""

import struct
from typing import Any

from app.domain.equipment._utils.real48_utils import (
    CR_MARKER,
    DOT_MARKER,
    DOUBLE_DOT_MARKER,
    SEMICOLON_MARKER,
    _extract_byte_parameters,
    _find_marker_index,
    _get_param_index,
    _read48_to_float,
)

# This format might be specific to how PAN files format their floats
value_format = "{:.2f}"


def _extract_iam_profile(
    *, start_index: int, byte_array: bytes
) -> list[dict[str, float]]:
    """Extracts the IAM (Incidence Angle Modifier) profile.

    Args:
        start_index: TODO: describe.
        byte_array: TODO: describe.
    """
    iam_profile = []

    for i in range(0, 45, 5):  # 0 to 44 step 5 (matches VB.NET loop)
        # Extract AOI value
        aoi_index = _get_param_index(start_index=start_index, offset_num=i)
        aoi_bytes = _extract_byte_parameters(
            byte_array=byte_array, start_index=aoi_index, num_bytes=6
        )
        aoi_raw = _read48_to_float(real48=aoi_bytes)
        aoi_formatted = value_format.format(aoi_raw)  # Keep for the check

        # Check if AOI is not null/empty (like VB.NET vbNullString check)
        if aoi_formatted != "":
            # Extract modifier value
            modifier_index = _get_param_index(start_index=start_index, offset_num=i + 1)
            modifier_bytes = _extract_byte_parameters(
                byte_array=byte_array, start_index=modifier_index, num_bytes=6
            )
            modifier_raw = _read48_to_float(real48=modifier_bytes)

            # Add to profile (only if AOI is not empty)
            iam_profile.append({"aoi": aoi_raw, "modifier": modifier_raw})
        # If AOI is empty, we skip this entry entirely (don't add to list)
    return iam_profile


def read_pan_binary(*, file_content: bytes) -> dict:
    """todo

    Args:
        file_content: TODO: describe.
    """
    data: dict[str, Any] = {}
    byte_array = file_content
    if not byte_array:
        raise ValueError("File is empty")

    # --- Find start indices for string parameters ---
    try:
        manu_start_index = _find_marker_index(
            marker=SEMICOLON_MARKER, start_index=0, byte_array=byte_array
        )
        panel_start_index = _find_marker_index(
            marker=DOT_MARKER, start_index=0, byte_array=byte_array
        )
        source_start_index = _find_marker_index(
            marker=DOT_MARKER, start_index=panel_start_index, byte_array=byte_array
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
            start_index=version_end_index,
            byte_array=byte_array,
        )
        technology_start_index = _find_marker_index(
            marker=DOUBLE_DOT_MARKER,
            start_index=year_start_index,
            byte_array=byte_array,
        )
        cells_in_series_start_index = _find_marker_index(
            marker=SEMICOLON_MARKER,
            start_index=technology_start_index,
            byte_array=byte_array,
        )
        cells_in_parallel_start_index = _find_marker_index(
            marker=SEMICOLON_MARKER,
            start_index=cells_in_series_start_index,
            byte_array=byte_array,
        )
        bypass_diodes_start_index = _find_marker_index(
            marker=SEMICOLON_MARKER,
            start_index=cells_in_parallel_start_index,
            byte_array=byte_array,
        )

        # --- Find start of Real48 encoded data ---
        cr_counter = 0
        real48_start_index = 0
        for i, byte in enumerate(byte_array):
            if byte == CR_MARKER:
                cr_counter += 1
            if cr_counter == 3:
                real48_start_index = i + 2  # Skip <CR><LF>
                break

        if real48_start_index == 0:
            return {"error": "Could not find start of Real48 data block."}

        # --- Extract string parameters ---
        # Note: latin-1 is used as it can decode any byte value without error
        data["Manufacturer"] = (
            byte_array[manu_start_index : panel_start_index - 1]
            .decode("latin-1")
            .strip()
        )
        data["Model"] = (
            byte_array[panel_start_index : source_start_index - 1]
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
            .replace("Version", "PVsyst")
            .strip()
        )
        data["Year"] = (
            byte_array[year_start_index : year_start_index + 4]
            .decode("latin-1")
            .strip()
        )
        data["Technology"] = (
            byte_array[technology_start_index : cells_in_series_start_index - 1]
            .decode("latin-1")
            .strip()
        )
        data["Cells_In_Series"] = (
            byte_array[cells_in_series_start_index : cells_in_parallel_start_index - 1]
            .decode("latin-1")
            .strip()
        )
        data["Cells_In_Parallel"] = (
            byte_array[cells_in_parallel_start_index : bypass_diodes_start_index - 1]
            .decode("latin-1")
            .strip()
        )

        # --- Parse Real48 encoded parameters ---
        param_map = {
            "PNom": 0,
            "VMax": 1,
            "Tolerance": 2,
            "AreaM": 3,
            "CellArea": 4,
            "GRef": 5,
            "TRef": 6,
            "Isc": 8,
            "muISC": 9,
            "Voc": 10,
            "muVocSpec": 11,
            "Imp": 12,
            "Vmp": 13,
            "BypassDiodeVoltage": 14,
            "RShunt": 17,
            "RSerie": 18,
            "RShunt_0": 23,
            "RShunt_exp": 24,
            "muPmp": 25,
        }

        for name, offset in param_map.items():
            start = _get_param_index(start_index=real48_start_index, offset_num=offset)
            end = start + 6
            param_bytes = byte_array[start:end]
            value = _read48_to_float(real48=param_bytes)
            if name == "Tolerance":
                value *= 100  # Convert to percentage
                if value > 100:
                    value = 0.0
            data[name] = value

        # --- Check for and Parse IAM Profile ---
        dot_counter = 0
        iam_start_index = 0
        dot_position = data["Version"].find(".")
        major_version = int(data["Version"][dot_position - 1 : dot_position])
        if major_version < 6:
            for i in range(real48_start_index + 170, len(byte_array)):
                if byte_array[i] == DOT_MARKER:
                    dot_counter += 1
                if dot_counter == 2:
                    iam_start_index = i + 4
                    break

        if iam_start_index > 0:
            data["IAMProfile"] = _extract_iam_profile(
                start_index=iam_start_index, byte_array=byte_array
            )

    except (IndexError, TypeError, struct.error) as e:
        return {"error": f"Failed to parse binary PAN file: {e}"}

    return data
