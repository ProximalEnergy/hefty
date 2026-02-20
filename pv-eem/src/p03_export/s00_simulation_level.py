from enum import StrEnum


class SimulationLevel(StrEnum):
    """SimulationLevel."""

    PLANE_OF_ARRAY_IRRADIANCE = "plane_of_array_irradiance"
    COMBINER = "combiner"
    INVERTER = "inverter"
    TRANSFORMER = "transformer"
    INTERCONNECTION = "interconnection"
