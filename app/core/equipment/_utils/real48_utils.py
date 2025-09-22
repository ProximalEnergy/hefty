"""
Utilities for parsing older PVsyst binary files that use Delphi's Real48 format.

This is based on:
    https://github.com/CanadianSolar/CASSYS/blob/b5487bb4e9e77174c805d64e3c960c46d357b7e2/CASSYS%20Interface/DatabaseImportModule.vba#L4
"""

# --- Constants ---
SEMICOLON_MARKER = 0x3B
DOT_MARKER = 0x09
DOUBLE_DOT_MARKER = 0x0A
FORWARD_SLASH_MARKER = 0x2F
CR_MARKER = 0x0D  # Carriage Return
VERTICAL_BAR_MARKER = 0xA6


# --- Supporting Functions ---
def _read48_to_float(*, real48: bytes) -> float:
    """
    Converts a 6-byte Delphi Real48 encoded value to a standard Python float.

    The format consists of:
    - 1 byte: Exponent (offset by 129)
    - 5 bytes: Mantissa, with the last bit of the 5th byte as the sign bit.
    """
    if not real48 or len(real48) != 6 or real48[0] == 0:
        return 0.0

    # The exponent is the first byte, with an offset of 129
    exponent = float(real48[0] - 129)

    mantissa = 0.0

    # Process the first 4 bytes of the mantissa
    # The division by 256 (or multiplication by 0.00390625) shifts the bytes
    for i in range(4, 0, -1):
        mantissa += real48[i]
        mantissa /= 256.0

    # Process the 5th byte of the mantissa
    mantissa += real48[5] & 0x7F  # Use only the first 7 bits
    mantissa /= 128.0  # equivalent to * 0.0078125
    mantissa += 1.0

    # Check the sign bit (the last bit of the 6th byte)
    if (real48[5] & 0x80) == 0x80:
        mantissa = -mantissa

    # Final calculation using the exponent
    return mantissa * (2.0**exponent)


def _find_marker_index(*, marker: int, start_index: int, byte_array: bytes) -> int:
    """
    Finds the index of the first occurrence of a hex marker after a start index.
    Returns the index right after the marker.
    """
    # bytearray.find is more efficient than a manual loop
    found_index = byte_array.find(bytes([marker]), start_index)
    if found_index != -1:
        return found_index + 1
    if found_index is None:
        raise ValueError(f"Marker {marker} not found in byte array")
    return found_index


def _get_param_index(*, start_index: int, offset_num: int) -> int:
    """Calculates the start index of a Real48 parameter."""
    return start_index + 6 * offset_num


def _extract_byte_parameters(
    *, byte_array: bytes, start_index: int, num_bytes: int
) -> bytes:
    """
    This function extracts bytes that form a single parameter from the original byte array
    (contains the bytes from the whole file) into a smaller byte array that it returns.
    """
    # Check bounds to avoid index errors
    if start_index + num_bytes > len(byte_array):
        raise IndexError(
            f"Not enough bytes: need {num_bytes} bytes starting at {start_index}"
        )

    # Extract the specified number of bytes starting at start_index
    param_byte_sequence = byte_array[start_index : start_index + num_bytes]

    return param_byte_sequence
