def calc_power_dc_nominal(*, inverter: dict):
    """Simple calculation of dc nominal power from maximum efficiency
        and nominal ac power.

        Caveats:
            * Should we be using maximum efficiency or euro efficiency?
            * cec efficiency is not provided in OND files

    Args:
        inverter: Description for inverter.
    """
    inverter["power_dc_nominal"] = (
        inverter["power_ac_nominal"] / inverter["max_efficiency"]
    )
    return inverter
