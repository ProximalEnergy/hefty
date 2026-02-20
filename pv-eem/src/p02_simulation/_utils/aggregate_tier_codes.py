import pandas as pd


def combine_unique_codes(series):
    # Split each string by comma, strip whitespace, and collect unique
    # values
    unique_codes = set()
    for codes in series:
        if pd.notna(codes):  # Check if the value is not NaN
            unique_codes.update([code.strip() for code in codes.split(",")])
    # Join the unique codes back into a single string
    return ", ".join(sorted(unique_codes))  # Sort for consistent ordering
