from datetime import datetime, timedelta


def generate_daily_ranges(
    *,
    start_str: str,
    end_str: str,
) -> list[tuple[datetime, datetime]]:
    """
    Generate a list of tuples containing start and end timestamps for each day
    between the given start and end dates (inclusive).

    Args:
        start_str (str): Start datetime in format 'YYYY-MM-DD HH:MM:SS'
        end_str (str): End datetime in format 'YYYY-MM-DD HH:MM:SS'

    Returns:
        list[tuple[datetime, datetime]]: List of (start, end) datetime tuples
            for each day
    """
    # Convert string inputs to datetime objects
    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    try:
        start_date = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
    except ValueError:
        raise (ValueError("Could not parse date"))

    # Initialize result list
    daily_ranges = []

    current_date_naive = datetime(
        start_date.year,
        start_date.month,
        start_date.day,
    )
    start_date_naive = start_date.replace(tzinfo=None)
    end_date_naive = end_date.replace(tzinfo=None)

    while current_date_naive <= end_date_naive:
        # Calculate day's start (00:00:00)
        day_start = current_date_naive

        # Calculate day's end (23:59:59)
        day_end = datetime(
            current_date_naive.year,
            current_date_naive.month,
            current_date_naive.day,
            23,
            59,
            59,
        )

        # Handle edge cases for first and last day
        if current_date_naive == datetime(
            start_date_naive.year,
            start_date_naive.month,
            start_date_naive.day,
        ):
            day_start = start_date_naive
        if current_date_naive == datetime(
            end_date_naive.year,
            end_date_naive.month,
            end_date_naive.day,
        ):
            day_end = end_date_naive

        daily_ranges.append((day_start, day_end))
        current_date_naive += timedelta(days=1)

    return daily_ranges


# Example usage:
if __name__ == "__main__":
    simulation_start = "2024-09-15 00:00:00"
    simulation_end = "2024-12-15 23:59:59"

    ranges = generate_daily_ranges(
        start_str=simulation_start,
        end_str=simulation_end,
    )
