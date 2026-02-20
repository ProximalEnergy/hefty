import datetime

import polars as pl
import pytz
import s3fs


def get_input_data(
    *,
    start_time: str,
):
    """
    Get Input Data for the model in production during a certain time frame
    """
    # --- Variables ---
    AWS_S3_BUCKET_NAME = "pv-expected-model-logs"
    start_datetime_with_offset = datetime.datetime.strptime(
        start_time, "%Y-%m-%d %H:%M:%S%z"
    )
    # print(start_datetime_with_offset)
    start_datetime = start_datetime_with_offset.astimezone(pytz.utc)
    end_datetime = start_datetime + datetime.timedelta(minutes=5)
    # print(f"UTC: {start_datetime}")

    # --- Authenticate with S3 ---
    fs = s3fs.S3FileSystem(asynchronous=False)
    files = fs.ls(f"{AWS_S3_BUCKET_NAME}/met")
    filtered_files = []

    if files:
        for file_path in files:
            # Extract just the filename without path
            filename = file_path.split("/")[-1]

            # Parse date and time from filename
            parts = filename.split("_")
            if len(parts) != 3:
                continue
            date_str = parts[0]  # "2025-04-24"
            time_str = parts[1]  # "16:16:30"
            # Combine date and time
            full_file_datetime_str = f"{date_str} {time_str}"

            try:
                # Parse the datetime as naive then just assign UTC timezone
                # without conversion
                full_file_datetime = datetime.datetime.strptime(
                    full_file_datetime_str, "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=pytz.utc)
                if start_datetime <= full_file_datetime <= end_datetime:
                    filtered_files.append(file_path)
            except ValueError:
                # Skip files that don't match the expected format
                print(f"Skipping file with invalid datetime format: {filename}")

    # --- QC ---
    if len(filtered_files) > 1:
        for file in filtered_files:
            print(f" - {file}")
        raise ValueError("Only one file can be selected at a time")

    # --- Read File ---
    print(f"Filtered files: {filtered_files}")
    file_path = filtered_files[0]
    with fs.open(file_path, "rb") as file:
        print(file_path)
        df = pl.read_parquet(file)  # type: ignore
        df.write_parquet(f"_tests/_artifacts/met_data_raw_{start_time[:-6]}.pq")
        print(df)


if __name__ == "__main__":
    pl.Config.set_tbl_cols(100)  # Show up to 100 columns
    pl.Config.set_tbl_rows(100)  # Show up to 100 rows
    get_input_data(
        start_time="2025-08-05 05:50:00-07:00",
    )
