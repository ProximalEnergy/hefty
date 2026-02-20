import pvlib


def calc_site_pressure(elevation):
    """Calculate atmospheric pressure at a given elevation using pvlib

    Args:
        elevation (float): Site elevation in meters

    Returns:
        float: Site pressure in Pascals
    """
    site_pressure = pvlib.atmosphere.alt2pres(elevation)
    return site_pressure
