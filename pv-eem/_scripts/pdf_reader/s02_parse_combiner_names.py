import re

import pandas as pd


def parse_combiner_names(
    df: pd.DataFrame,
):
    # Function to apply the transformation
    def transform_combiner_box(value):
        match = re.match(r"CB(\d+)-(\d+)", value)
        if match:
            part1 = match.group(1)
            part2 = match.group(2)
            return float(f"{part1}.{part2.zfill(2)}")
        return None

    # Apply the function to the column
    df["Combiner Box Schedule"] = df["Combiner Box Schedule"].apply(
        transform_combiner_box
    )

    return df
