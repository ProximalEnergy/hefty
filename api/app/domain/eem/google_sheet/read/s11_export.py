import s3fs

from app import settings


def export_system(
    *,
    system,
    project_name_short,
):
    """Export a system to S3

    Args:
        system: Description for system.
        project_name_short: Description for project_name_short.
    """

    # Environment Variables
    AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
    AWS_S3_BUCKET_NAME = settings.AWS_S3_BUCKET_NAME

    # Create S3 client
    fs = s3fs.S3FileSystem(
        key=AWS_ACCESS_KEY_ID,
        secret=AWS_SECRET_ACCESS_KEY,
    )

    with fs.open(f"{AWS_S3_BUCKET_NAME}/{project_name_short}.parquet", "wb") as f:
        system.to_parquet(path=f)

    return 200
