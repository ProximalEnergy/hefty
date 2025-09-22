import json
import logging
import time

import boto3
from app.v1.protected.pv_expected_energy.backfill.s00_separate_dates import (
    generate_daily_ranges,
)


def backfill_in_background(
    *,
    energy_model_version: str,
    project_name_short: str,
    simulation_start: str,
    simulation_end: str,
    **kwargs,
):
    # --- MAIN ---

    # Create Lambda client
    lambda_client = boto3.client("lambda", region_name="us-east-2")

    if energy_model_version == "live":
        energy_model_version_cleaned = "live"
    else:
        energy_model_version_cleaned = f"v{energy_model_version.replace('.', '-')}"

    # Run simulations
    date_ranges = generate_daily_ranges(
        start_str=simulation_start,
        end_str=simulation_end,
    )
    successful_invocations = 0
    failed_invocations = 0
    for i, date_range in enumerate(date_ranges):
        logging.info(f"backfill async call: {i + 1}/{len(date_ranges)}")

        # create payloads
        payload = {
            "body": {
                "project_name_short": project_name_short,
                "simulation_temporal_mode": "window",
                "simulation_start": str(date_range[0]),
                "simulation_end": str(date_range[1]),
            },
        }
        payload["body"].update(kwargs)

        try:
            # invoke lambda
            response = lambda_client.invoke(
                FunctionName=f"pv-simulation:{energy_model_version_cleaned}",
                InvocationType="Event",  # Asynchronous execution
                Payload=json.dumps(payload),
            )

            # Check the status code (202 is expected for async invocations)
            if response["StatusCode"] == 202:
                successful_invocations += 1
            else:
                failed_invocations += 1

        except Exception as e:
            failed_invocations += 1
            logging.warning(
                f"Failed to invoke Lambda for date range {date_range}: {str(e)}",
            )

        time.sleep(10)  # Wait for x seconds between invocations

    # Print summary
    logging.info("\n --- Invocation Summary: ---")
    logging.info(f"Total invocations: {len(date_ranges)}")
    logging.info(f"Successful invocations: {successful_invocations}")
    logging.info(f"Failed invocations: {failed_invocations}")
