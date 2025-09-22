import pvlib

PROJECT_DEVICE_MAP = {
    "assembly_1": {
        "module": "longi",
        "inverter": "tmeic",
    },
    "assembly_2": {
        "module": "longi",
        "inverter": "tmeic",
    },
    "assembly_3": {
        "module": "longi",
        "inverter": "tmeic",
    },
    "fiddlers_canyon_3": {
        "module": "sunedison",
        "inverter": "power_electronics",
    },
    "lancaster": {
        "module": "first_solar",
        "inverter": "sungrow",
    },
    "snipesville_2": {
        "module": "first_solar",
        "inverter": "sungrow",
    },
    "double_black_diamond": {
        "module": "first_solar",
        "inverter": "sungrow_sg3600ud-mv",
    },
    "sun_streams_3": {
        "module": "first_solar",
        "inverter": "sungrow_sg3600ud-mv",
    },
    "sun_streams_4": {
        "module": "first_solar",
        "inverter": "sungrow_sg3600ud-mv",
    },
    "serrano": {
        "module": "first_solar",
        "inverter": "sungrow_sg3600ud-mv",
    },
}

PROJECT_LOCATION_MAP = {
    "assembly_1": pvlib.location.Location(
        latitude=42.9856,
        longitude=-83.9283,
        tz="America/Detroit",
        altitude=0,  # TODO
        name="Assembly 1",
    ),
    "assembly_2": pvlib.location.Location(
        latitude=42.9856,
        longitude=-83.9283,
        tz="America/Detroit",
        altitude=0,  # TODO
        name="Assembly 2",
    ),
    "assembly_3": pvlib.location.Location(
        latitude=42.9856,
        longitude=-83.9283,
        tz="America/Detroit",
        altitude=0,  # TODO
        name="Assembly 3",
    ),
    "fiddlers_canyon_3": pvlib.location.Location(
        latitude=37.73108,
        longitude=-113.21947,
        tz="America/Denver",
        altitude=1689.0,
        name="Fiddlers Canyon 3",
    ),
    "lancaster": pvlib.location.Location(
        latitude=31.4753,
        longitude=-84.7411,
        tz="America/New_York",
        altitude=0,  # TODO
        name="Lancaster",
    ),
    "snipesville_2": pvlib.location.Location(
        latitude=31.71,
        longitude=-82.73,
        tz="America/New_York",
        altitude=0,  # TODO
        name="Snipesville 2",
    ),
    "double_black_diamond": pvlib.location.Location(
        latitude=39.53,
        longitude=-89.89,
        tz="America/Chicago",
        altitude=0,  # TODO
        name="Double Black Diamond",
    ),
    "sun_streams_3": pvlib.location.Location(
        latitude=33.337,
        longitude=-112.817,
        tz="America/Phoenix",
        altitude=0,  # TODO
        name="Sun Streams 3",
    ),
    "sun_streams_4": pvlib.location.Location(
        latitude=33.337,
        longitude=-112.817,
        tz="America/Phoenix",
        altitude=0,  # TODO
        name="Sun Streams 4",
    ),
    "serrano": pvlib.location.Location(
        latitude=32.49203885358152,
        longitude=-111.30213385452477,
        tz="America/Phoenix",
        altitude=578,
        name="Serrano",
    ),
}

PROJECT_PARAMS = {
    "assembly_1": {
        "sensor_type_name_short": "pv_pcs_module_ac_power",
        "device_type_id": 2,
        "scale": 1.1,
    },
    "assembly_2": {
        "sensor_type_name_short": "pv_pcs_module_ac_power",
        "device_type_id": 2,
        "scale": 1.05,
    },
    "assembly_3": {
        "sensor_type_name_short": "pv_pcs_module_ac_power",
        "device_type_id": 2,
        "scale": 1.1,
        "meter_loss": 0.9779,
    },
    "fiddlers_canyon_3": {
        "sensor_type_name_short": "pv_pcs_ac_power",
        "device_type_id": 2,
        "scale": 1.1,
    },
    "lancaster": {
        "sensor_type_name_short": "pv_pcs_ac_power",
        "device_type_id": 2,
        "scale": 0.9,
    },
    "snipesville_2": {
        "sensor_type_name_short": "pv_pcs_ac_power",
        "device_type_id": 2,
        "scale": 0.91,
        "meter_loss": 0.9716,
    },
    "double_black_diamond": {
        "sensor_type_name_short": "pv_pcs_ac_power",
        "device_type_id": 2,
        "scale": 0.9,
        "meter_loss": 0.975,
    },
    "sun_streams_3": {
        "sensor_type_name_short": "pv_pcs_ac_power",
        "device_type_id": 2,
        "scale": 0.9,
        "meter_loss": 0.975,
    },
    "sun_streams_4": {
        "sensor_type_name_short": "pv_pcs_ac_power",
        "device_type_id": 2,
        "scale": 0.95,
        "meter_loss": 0.975,
    },
    "serrano": {
        "sensor_type_name_short": "pv_pcs_ac_power",
        "device_type_id": 2,
        "scale": 0.9,
        "meter_loss": 0.975,
    },
}

MODULE_DATA = {
    "longi": {
        "gamma_pdc": -0.0037,
    },
    "first_solar": {
        "gamma_pdc": -0.0032,
    },
    "sunedison": {
        "gamma_pdc": -0.0032,  # PLACEHOLDER
    },
}

INVERTER_DATA = {
    "tmeic": {
        "pdc0": 840_000 / 0.985,
        "eta_inv_nom": 0.985,
    },
    "sungrow": {
        "pdc0": 250_000 / 0.985,
        "eta_inv_nom": 0.985,
    },
    "sungrow_sg3600ud-mv": {
        "pdc0": 3_600_000 / 0.985,
        "eta_inv_nom": 0.985,
    },
    "power_electronics": {
        "pdc0": 150_000 / 0.985,
        "eta_inv_nom": 0.985,
    },  # PLACEHOLDER
}
