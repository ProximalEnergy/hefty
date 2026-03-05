import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz

# Add pv-eem to path to allow imports
# Assuming running from 'mono' root
sys.path.append(str(Path("pv-eem").resolve()))
sys.path.append(str(Path("pv-eem/src").resolve()))

from _tests.snapshot_test_helpers import read_snapshot_inputs

SNAPSHOT_NAME = "nuisance_alarm_test"
SIMULATION_START = "2025-04-24 19:25:00"
SIMULATION_END = "2025-04-24 19:30:00"


def inspect():
    print(f"Inspecting snapshot: {SNAPSHOT_NAME}")

    try:
        # Load without filtering first to see what's in there
        print("\n--- Loading FULL snapshot ---")

        inputs_full = read_snapshot_inputs(snapshot_name=SNAPSHOT_NAME)
        met_index = inputs_full.indeces.met_time_index.data
        project_tz = inputs_full.project.time_zone

        print(f"Project Timezone: {project_tz}")
        print(f"Total met data points: {len(met_index)}")

        if not met_index.empty:
            print(f"Start: {met_index['time'].min()}")
            print(f"End:   {met_index['time'].max()}")
            print(f"Timezone in DF: {met_index['time'].dt.tz}")

            print("\nSample met data (time column):")
            print(met_index.head())
            print("...")
            print(met_index.tail())

        print("\n--- Loading FILTERED snapshot ---")
        print(f"Request: {SIMULATION_START} to {SIMULATION_END}")

        inputs_filtered = read_snapshot_inputs(
            snapshot_name=SNAPSHOT_NAME,
            simulation_start=SIMULATION_START,
            simulation_end=SIMULATION_END,
        )

        met_index_filtered = inputs_filtered.indeces.met_time_index.data
        print(f"Filtered met data points: {len(met_index_filtered)}")

        if len(met_index_filtered) == 0:
            print("!!! NO DATA RETURNED !!!")

            # Debug why
            tz = pytz.timezone(project_tz)
            start_dt = tz.localize(
                datetime.strptime(SIMULATION_START, "%Y-%m-%d %H:%M:%S")
            )
            end_dt = tz.localize(datetime.strptime(SIMULATION_END, "%Y-%m-%d %H:%M:%S"))
            print(f"Localized Request Start: {start_dt}")
            print(f"Localized Request End:   {end_dt}")

            # Check overlap
            if not met_index.empty:
                full_start = met_index["time"].min()
                full_end = met_index["time"].max()

                print(f"Full Data Range: {full_start} to {full_end}")

                if start_dt > full_end:
                    print("Request is AFTER data range.")
                elif end_dt < full_start:
                    print("Request is BEFORE data range.")
                else:
                    print("Request overlaps data range, but no exact matches found?")
                    # Check for times within range
                    mask = (met_index["time"] >= start_dt) & (
                        met_index["time"] <= end_dt
                    )
                    print(f"Rows matching mask: {mask.sum()}")

        else:
            print(met_index_filtered)
            print("\nMet Data GHI check:")
            if hasattr(inputs_filtered.met_data, "met_data"):
                print(inputs_filtered.met_data.met_data[["ghi"]])
            else:
                print("Met data attribute structure unknown.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    inspect()
