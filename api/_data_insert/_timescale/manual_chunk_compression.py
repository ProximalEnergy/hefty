"""
Manual Chunk Compression Script for TimescaleDB Hypertables

This script performs manual compression of TimescaleDB hypertable chunks for a specified
date range. It's designed to compress chunks older than each date in the range, which
helps optimize storage and query performance.

Features:
- Processes chunks day by day for a configurable date range
- Provides detailed logging with timestamps and performance metrics
- Reports compression statistics including space savings in GB
- Calculates total execution time and average time per day
- Uses TimescaleDB's hypertable_columnstore_stats() function for detailed metrics

Configuration:
- PROJECT_NAME_SHORT: Database schema name containing the hypertable
- HYPERTABLE_NAME: Name of the hypertable to compress
- START_DATE/END_DATE: Date range for chunk compression (exclusive of end date)

Usage:
    python manual_chunk_compression.py

The script will:
1. Log the compression job details (date range, total dates)
2. Process each date sequentially, compressing chunks older than that date
3. Log individual compression times and overall progress
4. Provide a final summary with total execution time and averages
5. Report detailed compression statistics including space savings

Note: This script requires appropriate database permissions to execute
compress_chunk() and access hypertable statistics.
"""

from time import time

import pandas as pd
import psycopg2
from app.logger import logger

from .. import utils

PROJECT_NAME_SHORT = "double_black_diamond"
HYPERTABLE_NAME = "data_timeseries"
START_DATE = "2025-09-01"
END_DATE = "2025-09-02"

response = (
    input(
        "Do you want to continue with the compression?\n"
        f"  PROJECT_NAME_SHORT: {PROJECT_NAME_SHORT}\n"
        f"  HYPERTABLE_NAME: {HYPERTABLE_NAME}\n"
        f"  START_DATE: {START_DATE}\n"
        f"  END_DATE: {END_DATE}\n"
        "(y/N): "
    )
    .strip()
    .lower()
)

if response not in ["y", "yes"]:
    logger.info("Compression cancelled by user.")
    exit(0)

date_range = pd.date_range(start=START_DATE, end=END_DATE, freq="1d", inclusive="left")

# Log compression job details
total_dates = len(date_range)
logger.info(
    f"Starting compression job: {START_DATE} to {END_DATE} "
    f"({total_dates} dates to process)"
)

overall_start_time = time()

for date in date_range:
    start_time = time()

    newer_than = (date - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    older_than = date.strftime("%Y-%m-%d")
    logger.info(f"Processing date: {date}")

    with psycopg2.connect(dsn=utils.CONNECTION_STRING) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                select compress_chunk(c)
                from show_chunks(
                    '{PROJECT_NAME_SHORT}.{HYPERTABLE_NAME}',
                    newer_than => date '{newer_than}',
                    older_than => date '{older_than}'
                ) c;
                """
            )
            result = cursor.fetchall()

    end_time = time()
    execution_time = end_time - start_time
    logger.info(f"Compression completed in {execution_time:.1f} seconds")

# Log final summary
overall_end_time = time()
total_execution_time = overall_end_time - overall_start_time
average_per_day = total_execution_time / total_dates if total_dates > 0 else 0

logger.info(
    f"Compression job completed: {total_dates} dates processed in "
    f"{total_execution_time:.1f} seconds (avg: {average_per_day:.1f}s per day)"
)

# Report compression statistics and space savings
logger.info("Retrieving compression statistics...")
with psycopg2.connect(dsn=utils.CONNECTION_STRING) as conn:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM hypertable_columnstore_stats("
            f"'{PROJECT_NAME_SHORT}.{HYPERTABLE_NAME}');"
        )
        stats = cursor.fetchone()

        if stats:
            # Extract statistics
            total_chunks = stats[0]
            compressed_chunks = stats[1]
            before_total_bytes = stats[5]  # before_compression_total_bytes
            after_total_bytes = stats[9]  # after_compression_total_bytes

            if before_total_bytes and after_total_bytes:
                space_saved_bytes = before_total_bytes - after_total_bytes
                compression_ratio = (space_saved_bytes / before_total_bytes) * 100

                # Convert bytes to GB
                before_gb = before_total_bytes / (1024**3)
                after_gb = after_total_bytes / (1024**3)
                space_saved_gb = space_saved_bytes / (1024**3)

                logger.info(
                    "Compression Statistics: "
                    f"{compressed_chunks}/{total_chunks} chunks compressed"
                )
                logger.info(
                    f"Space Savings: {space_saved_gb:.3f} GB saved "
                    f"({compression_ratio:.2f}% reduction)"
                )
                logger.info(f"Size: {before_gb:.3f} GB → {after_gb:.3f} GB")
            else:
                logger.warning("No compression statistics available")
        else:
            logger.warning("Could not retrieve compression statistics")
