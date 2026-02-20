from dataclasses import dataclass

from interfaces import (
    Indeces,
    InverterDeviceSeries,
    InverterTimeSeries,
)
from p01_get_data.s00_get_simulation_config import SimulationConfig
from p01_get_data.source_proximal.s09_get_inverter_data import Inverter
from p02_simulation.p4_dc_iv.c_dc_iv import PowerAtCombiner
from p02_simulation.p5_inverter.s00_dc_wiring_to_inverter import InverterDCWires
from p02_simulation.p5_inverter.s01_combine_iv_curves import InverterInputTerminal
from p02_simulation.p5_inverter.s02_calc_efficiency import InverterPowerAfterEfficiency


@dataclass(init=False, slots=True)
class InverterPower:
    """InverterPower."""

    time: InverterTimeSeries
    power: InverterTimeSeries
    current: InverterTimeSeries
    voltage: InverterTimeSeries
    device_ids: InverterTimeSeries
    equipment_ids: InverterTimeSeries
    tier: InverterTimeSeries
    tier_codes: InverterTimeSeries

    def __init__(
        self,
        *,
        simulation_config: SimulationConfig,
        indeces: Indeces,
        power_at_combiner: PowerAtCombiner,
        inverters: Inverter,
        inverter_device_ids: InverterDeviceSeries,
        inverter_equipment_ids: InverterDeviceSeries,
    ):
        """Calculate inverter power given:
        - inverter parameters
        - input DC iv curves
        """
        iv_combiners_wiring = InverterDCWires(
            model=simulation_config.dc_wiring_to_inverter,
            indeces=indeces,
            power_at_combiner=power_at_combiner,
        )

        iv_inverters = InverterInputTerminal(
            indeces=indeces,
            iv_combiners_wiring=iv_combiners_wiring,
            inverter_equipment_ids=inverter_equipment_ids,
            inverter_device_ids=inverter_device_ids,
        )

        inverters_after_efficiency = InverterPowerAfterEfficiency(
            model=simulation_config.inverter_efficiency,
            indeces=indeces,
            iv_inverters=iv_inverters,
            inverters=inverters,
        )

        # Quality Assurance
        self.time = InverterTimeSeries(indeces.inverter_time_index.loc[:, "time"])
        self.device_ids = InverterTimeSeries(
            indeces.inverter_time_index.loc[:, "pcs_device_id"]
        )
        self.power = InverterTimeSeries(inverters_after_efficiency.power)
        self.current = InverterTimeSeries(inverters_after_efficiency.current)
        self.voltage = InverterTimeSeries(inverters_after_efficiency.voltage)
        self.equipment_ids = InverterTimeSeries(iv_inverters.equipment_ids)
        self.tier = InverterTimeSeries(inverters_after_efficiency.tier)
        self.tier_codes = InverterTimeSeries(inverters_after_efficiency.tier_codes)
