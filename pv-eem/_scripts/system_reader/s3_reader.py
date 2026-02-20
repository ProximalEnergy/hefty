import argparse
import io  # Required for BytesIO
import logging
import os

import boto3  # Explicitly imported for S3 client
import polars as pl
from dotenv import load_dotenv


def get_system_data(
    *,  # Enforce keyword-only arguments as per user's custom instruction
    project_name_short: str,
):
    """
    Get system mechanical and electrical components from S3.
    Args:
        project_name_short: used to construct the S3 object key.
    """

    # --- Environment Variables ---
    load_dotenv()
    AWS_S3_BUCKET_NAME: str | None = os.getenv("AWS_S3_BUCKET_NAME")
    match AWS_S3_BUCKET_NAME:
        case None:
            raise ValueError("AWS_S3_BUCKET_NAME is missing from .env file")
        case _:
            pass

    # --- Construct S3 Object Key ---
    # The full S3 URI for logging/display
    s3_full_uri = f"s3://{AWS_S3_BUCKET_NAME}/{project_name_short}.parquet"
    # The Key parameter in boto3.client.get_object only needs object key within bucket
    s3_object_key = f"{project_name_short}.parquet"

    print(f"Attempting to read Parquet object: {s3_full_uri} using boto3 and polars.")

    try:
        # Initialize Boto3 S3 client
        # boto3 will automatically look for credentials in standard locations
        # (environment variables, ~/.aws/credentials, IAM roles, etc.).
        s3_client = boto3.client("s3")

        # Get the S3 object content into a BytesIO buffer
        response = s3_client.get_object(Bucket=AWS_S3_BUCKET_NAME, Key=s3_object_key)
        # The 'Body' is a StreamingBody object; read its content into BytesIO
        buffer = io.BytesIO(response["Body"].read())

        # Read the Parquet data from the BytesIO buffer using Polars
        system = pl.read_parquet(buffer)

        # --- Create local directory if it doesn't exist ---
        output_dir = "_scripts/system_reader"
        os.makedirs(output_dir, exist_ok=True)

        system.write_csv(f"{output_dir}/{project_name_short}_system.csv")
        print("Successfully read from S3 and wrote to CSV:")
        print(system)

    except s3_client.exceptions.NoSuchKey:  # pyright: ignore
        logging.critical(
            f"NoSuchKey Error: The file '{s3_object_key}' "
            f"was not found in bucket '{AWS_S3_BUCKET_NAME}'. "
            "This typically means the key does not exist in the specified bucket."
        )
    except s3_client.exceptions.ClientError as e:  # pyright: ignore
        # Catch specific ClientError for permission issues (e.g., AccessDenied)
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "AccessDenied":
            logging.critical(
                f"AccessDenied Error: Permission denied to S3 object '{s3_full_uri}'. "
                f"Ensure 's3:GetObject' permission is granted for this resource. Error: {e}"
            )
        else:
            logging.critical(
                f"A Boto3 ClientError occurred while reading {s3_full_uri}: {e}"
            )
    except Exception as e:
        logging.critical(
            f"An unexpected error occurred while trying to read {s3_full_uri}: {e}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get system data from S3")
    parser.add_argument(
        "project_name_short",
        help="The short name of the project, used to construct the S3 object key",
    )

    args = parser.parse_args()

    get_system_data(
        project_name_short=args.project_name_short,
    )
