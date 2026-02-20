def qc_times(
    simulation_temporal_mode: str,
    simulation_start: str | None,
    simulation_end: str | None,
    ENVIRONMENT: str,
) -> tuple[str, str]:
    """Check if simulation start and end times are valid"""
    # If PROD and instantaneous, simulation_time doesn't matter
    # since NOW() will be used instead.  Just set a random date
    # to make later functions happy
    if (
        ENVIRONMENT == "PROD"
        and simulation_temporal_mode == "instantaneous"
        and not simulation_start
    ):
        simulation_start = "2020-10-20 00:00:00"

    if (
        ENVIRONMENT == "PROD"
        and simulation_temporal_mode == "instantaneous"
        and not simulation_end
    ):
        simulation_end = "2020-10-20 23:59:59"

    # Type check to make sure that we have a simulation_time by this point
    if not simulation_start:
        raise ValueError("simulation_start must be provided")
    if not simulation_end:
        raise ValueError("simulation_end must be provided")

    return simulation_start, simulation_end
