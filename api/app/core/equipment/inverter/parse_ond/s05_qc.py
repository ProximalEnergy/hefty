def validate_inverter_config(*, inverter: dict) -> dict:
    """
    Validates inverter configuration dictionary for required keys and non-empty lists.

    Args:
        inverter: Dictionary containing inverter configuration

    Returns:
        (is_valid, errors): Tuple containing validation status and list of error messages
    """
    required_keys = {
        # Book-keeping
        "manufacturer",
        "model",
        # Operating window
        "voltage_mpp_min",
        "voltage_mpp_max",
        "voltage_min",
        "voltage_max",
        "current_max",
        "power_at_reference_temp",
        "reference_temp",
        "voltage_nominal_efficiency",
        "efficiency_at_low_voltage",
        "efficiency_at_mid_voltage",
        "efficiency_at_high_voltage",
        # Efficiency
        "power_ac_nominal",
        "power_dc_nominal",
        "voltage_dc_nominal",
        "power_start_up",
        "night_tare",
        # Sandia
        "c0",
        "c1",
        "c2",
        "c3",
    }

    list_keys = {
        "power_at_reference_temp",
        "reference_temp",
        "voltage_nominal_efficiency",
        "efficiency_at_low_voltage",
        "efficiency_at_mid_voltage",
        "efficiency_at_high_voltage",
    }

    errors = []

    # Check for missing keys
    missing_keys = required_keys - set(inverter.keys())
    if missing_keys:
        errors.append(f"Missing required keys: {', '.join(sorted(missing_keys))}")

    # Check list fields
    for key in list_keys:
        if key in inverter and not isinstance(inverter[key], (list, tuple)):
            errors.append(f"Key '{key}' must be a list or tuple")
        elif key in inverter and not inverter[key]:
            errors.append(f"Key '{key}' cannot be empty")

    # --- Raise ---
    if len(errors) > 0:
        raise ValueError(errors)

    return inverter
