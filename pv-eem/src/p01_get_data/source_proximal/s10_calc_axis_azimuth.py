def calc_axis_azimuth(latitude: float) -> float:
    """Calculates the axis azimuth of the tracker entirely based on the
    latitude of the site
    """
    match latitude:
        case latitude if latitude < 0.0:
            axis_azimuth = 0.0
        case _:
            axis_azimuth = 180.0

    return axis_azimuth
