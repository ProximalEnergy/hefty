import mimetypes

import boto3
from fastapi import APIRouter

DESCRIPTION_404 = "AWS action not found"

router = APIRouter(prefix="/aws", tags=["aws"])


@router.get("/retrieve-presigned-url")
def retrieve_presigned_url(
    *,
    bucket_name: str,
    file_path: str,
):
    """
    Retrieve a presigned URL for a file in S3.

    Args:
        bucket_name (str): The name of the S3 bucket.
        file_path (str): The path to the file in S3.

    Returns:
        str: A presigned URL for the file.
    """
    object_name = file_path.split("/")[-1] if "/" in file_path else file_path
    content_type, _ = mimetypes.guess_type(object_name)  # type: ignore
    s3_client = boto3.client("s3", region_name="us-east-2")
    if content_type is None:
        content_type = "application/octet-stream"  # Default to binary if unknown
    # NOTE: This ensures the file is downloaded correctly in the browser.
    content_disposition = f'attachment; filename="{object_name}"'

    # Generate a pre-signed URL for a file
    presigned_url = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": bucket_name,
            "Key": file_path,
            "ResponseContentDisposition": content_disposition,
        },
        ExpiresIn=3600,  # Link expiration in seconds (1 hour)
    )
    return presigned_url


@router.get("/listdir")
def listdir(
    *,
    bucket_name: str,
    path: str | None = None,
    project_prefix: str | None = None,
):
    """
    List the contents of a directory in S3.

    Args:
        bucket_name (str): The name of the S3 bucket.
        path (Optional[str]): The path to the directory in S3.
        project_prefix (Optional[str]): The name_short of the project to filter the
            contents of the directory.

    Returns:
        List[Contents]: A list of the contents of the directory as dictionaries.
        Dictionary keys are ["Key", "LastModified", "ETag", "Size",
        "StorageClass"].
    """
    if path is None:
        path = ""
    s3_client = boto3.client("s3", region_name="us-east-2")
    data = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=path)
    contents = data.get("Contents", []) or []
    if project_prefix is None:
        return [file for file in contents if not file["Key"].endswith("/")]

    normalized_path = path.rstrip("/") if path else ""
    project_filter_prefix = (
        f"{normalized_path}/" if normalized_path else ""
    ) + project_prefix
    return [
        file
        for file in contents
        if not file["Key"].endswith("/")
        and file["Key"].startswith(project_filter_prefix)
    ]
