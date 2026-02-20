import io
import uuid
from datetime import datetime

import boto3
import polars as pl


def log_met_data(
    *,
    met_data: pl.DataFrame,
    soiling_data: pl.DataFrame,
):
    """Log input DataFrame to S3 before processing."""
    # Create a unique identifier for this execution
    execution_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H:%M:%S")

    # Set up S3 client
    s3_client = boto3.client("s3")
    bucket_name = "pv-expected-model-logs"

    # Log the actual data
    buffer = io.BytesIO()
    met_data.write_parquet(buffer)
    buffer.seek(0)

    s3_client.put_object(
        Bucket=bucket_name,
        Key=f"met/{timestamp}_{execution_id}.parquet",
        Body=buffer.getvalue(),
    )

    # Log the actual data
    buffer = io.BytesIO()
    soiling_data.write_parquet(buffer)
    buffer.seek(0)

    s3_client.put_object(
        Bucket=bucket_name,
        Key=f"soil/{timestamp}_{execution_id}.parquet",
        Body=buffer.getvalue(),
    )

    return execution_id
