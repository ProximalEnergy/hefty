import numpy as np
import pvlib


def calc_fit_sandia(
    *,
    inverter: dict,
):
    """
    Calc parameters necessary for inverter model
    """

    # Extract data from efficiency dictionaries
    ac_power_low = [x[1] for x in inverter["efficiency_at_low_voltage"]]
    ac_power_mid = [x[1] for x in inverter["efficiency_at_mid_voltage"]]
    ac_power_high = [x[1] for x in inverter["efficiency_at_high_voltage"]]
    ac_power = np.concatenate([ac_power_low, ac_power_mid, ac_power_high])

    dc_power_low = [x[0] for x in inverter["efficiency_at_low_voltage"]]
    dc_power_mid = [x[0] for x in inverter["efficiency_at_mid_voltage"]]
    dc_power_high = [x[0] for x in inverter["efficiency_at_high_voltage"]]
    dc_power = np.concatenate([dc_power_low, dc_power_mid, dc_power_high])

    # Get voltage levels from voltage_nominal_efficiency
    v_min, v_nom, v_max = inverter["voltage_nominal_efficiency"]

    # Create voltage arrays
    dc_voltage = np.concatenate(
        [
            np.repeat(v_min, len(ac_power_low)),
            np.repeat(v_nom, len(ac_power_mid)),
            np.repeat(v_max, len(ac_power_high)),
        ],
    )

    # Create voltage level labels
    dc_voltage_level = np.concatenate(
        [
            np.repeat("Vmin", len(ac_power_low)),
            np.repeat("Vnom", len(ac_power_mid)),
            np.repeat("Vmax", len(ac_power_high)),
        ],
    )

    sandia = pvlib.inverter.fit_sandia(
        ac_power=ac_power,
        dc_power=dc_power,
        dc_voltage=dc_voltage,
        dc_voltage_level=dc_voltage_level,
        p_ac_0=inverter["power_ac_nominal"],
        p_nt=inverter["night_tare"],
    )
    # Skip updating certain keys in the sandia output
    exclude_keys = [
        "Paco",
        "p_nt",
    ]
    sandia = {k: v for k, v in sandia.items() if k not in exclude_keys}
    inverter.update((k, v) for k, v in sandia.items())

    # Change the name of some keys
    inverter["power_dc_nominal"] = inverter.pop("Pdco")
    inverter["voltage_dc_nominal"] = inverter.pop("Vdco")
    inverter["power_start_up"] = inverter.pop("Pso")
    inverter["c0"] = inverter.pop("C0")
    inverter["c1"] = inverter.pop("C1")
    inverter["c2"] = inverter.pop("C2")
    inverter["c3"] = inverter.pop("C3")

    return inverter
