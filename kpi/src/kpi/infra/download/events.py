import pandas as pd
from core.crud.project.events import get_windowed_events
from core.db_query import OutputType


def download_events_df(
    project_name_short: str,
    start_tz_aware: pd.Timestamp,
    end_tz_aware: pd.Timestamp,
    device_type_ids: list[int],
) -> pd.DataFrame:
    events = get_windowed_events(
        start=start_tz_aware,
        end=end_tz_aware,
        deep=False,
        include_underperformance=False,
        failure_mode_ids=None,
        device_type_ids=device_type_ids,
    )

    df_events = events.get(schema=project_name_short, output_type=OutputType.PANDAS)

    # only keep the necessary columns
    df_events = df_events[["device_id", "time_start", "time_end", "device_type_id"]]
    # clip start time to the start of the context
    df_events["time_start"] = df_events["time_start"].clip(lower=start_tz_aware)  # type: ignore[call-overload]
    # if time end is after end of context, set it to NaN
    df_events["time_end"] = df_events["time_end"].where(  # type: ignore[call-overload]
        df_events["time_end"] <= end_tz_aware, pd.NaT
    )

    return df_events
