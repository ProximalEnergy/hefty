from collections.abc import Callable
from typing import Any

import xarray as xr
from kpi_pipeline.base.enums import DataType
from kpi_pipeline.base.models import ContextModel, CoordCombinerModel
from kpi_pipeline.base.protocols import CalcProtocol, Implements, ProcessProtocol
from kpi_pipeline.domain.bess import (
    average_while_charging,
    average_while_discharging,
    bess_string_complete_availability,
    charging_cycles_from_soc,
    cycle_count_from_soc,
    daily_average_c_rate,
    daily_average_c_rate_charging,
    discharging_cycles_from_soc,
    maximum_continuous_discharge,
)
from kpi_pipeline.domain.general import (
    accumulate_energy_then_filter_by_capacity,
    accumulate_energy_then_verify_by_capacity,
    filter_by_capacity,
    verify_by_capacity,
    weighted_average,
)
from kpi_pipeline.domain.pv.module_state_of_health import (
    pv_dc_combiner_module_excess_degradation,
)
from kpi_pipeline.domain.pv.pvlib_integration import theoretical_poa_irradiance
from kpi_pipeline.domain.solar import (
    REFERENCE_IRRADIANCE,
    combiner_mechanical_availability,
    curtailed_power_from_eem,
    dc_field_health,
    mechanical_availability,
    performance_index,
    performance_ratio,
    tracker_availability,
    tracker_deviation_from_setpoint,
    tracker_setpoint_deviation_from_median,
)
from kpi_pipeline.domain.solv_contract import (
    solv_guarantee_availability,
    solv_period_kwh_lost,
    solv_period_kwh_produced,
)
from kpi_pipeline.infra.calc_function_checker import verify_calc_function_alignment
from kpi_pipeline.infra.coord_mapping import coord_combiner
from kpi_pipeline.infra.exceptions import DatasetAccessError, ValidationError
from kpi_pipeline.infra.utils import optional, select
from pydantic import BaseModel, ConfigDict


def _field_is_input(field: str, value: Any) -> bool:
    return isinstance(value, str) and (field != "output_dtype")


class CalcBase(BaseModel):
    output_dtype: DataType = DataType.FLOAT
    model_config = ConfigDict(extra="forbid")

    def expected_inputs(self) -> list[str]:
        """Automatically determine expected inputs from dataclass fields."""
        return [
            value
            for field, value in self.model_dump().items()
            if _field_is_input(field, value)
        ]


calc = Implements[CalcProtocol].decorator


def domain_calc(
    domain_function: Callable,
) -> Callable[[type[CalcBase]], type[CalcBase]]:
    def decorator(cls: type[CalcBase]) -> type[CalcBase]:
        problems = verify_calc_function_alignment(cls, domain_function)
        if problems:
            error_msg = "Calc function alignment issues:\n" + "\n".join(
                f"  • {problem}" for problem in problems
            )
            raise ValueError(error_msg)
        return cls

    return decorator


class CalcProcess(CalcProtocol):
    def __init__(
        self,
        calc: CalcProtocol,
        process: ProcessProtocol | None = None,
        output_dtype: DataType = DataType.FLOAT,
    ):
        self.calc_func = calc
        self.process_func = process
        self.output_dtype = output_dtype

    def __call__(
        self,
        *,
        dataset: xr.Dataset,
        context: ContextModel,
    ):
        x = self.calc_func(dataset=dataset, context=context)
        if self.process_func is not None:
            x = self.process_func(x=x, context=context)
        return x

    def expected_inputs(self) -> list[str]:
        return self.calc_func.expected_inputs()


@calc
class ProcessCalc:
    def __init__(
        self,
        *,
        var: str,
        process: ProcessProtocol,
        output_dtype: DataType = DataType.FLOAT,
    ):
        self.var = var
        self.process = process
        self.output_dtype = output_dtype

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return self.process(x=select(dataset, self.var), context=context)

    def expected_inputs(self) -> list[str]:
        return [self.var]


@calc
class SelectCalc(CalcBase):
    var: str

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return select(dataset, self.var)


@calc
class FillNACalc:
    def __init__(
        self,
        vars: list[str],
        allow_missing_fields: bool = False,
        output_dtype: DataType = DataType.FLOAT,
    ):
        self.vars = vars
        self.allow_missing_fields = allow_missing_fields
        self.output_dtype = output_dtype

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        x = xr.DataArray()
        for var in self.vars:
            try:
                x = x.fillna(select(dataset, var))
            except DatasetAccessError:
                if not self.allow_missing_fields:
                    raise
        return x

    def expected_inputs(self) -> list[str]:
        return self.vars


@calc
class VerifyBetweenFieldsCalc(CalcBase):
    target_var: str
    min_var: str | None = None
    max_var: str | None = None

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        target = select(dataset, self.target_var)
        min_array = optional(dataset, self.min_var)
        if min_array is not None:
            if (target < min_array).any():
                raise ValidationError(
                    f"values below min threshold from {self.min_var}."
                )
        max_array = optional(dataset, self.max_var)
        if max_array is not None:
            if (target > max_array).any():
                raise ValidationError(
                    f"values above max threshold from {self.max_var}."
                )
        return target


@calc
class QuotientCalc(CalcBase):
    numerator_var: str
    denominator_var: str

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return select(dataset, self.numerator_var) / select(
            dataset, self.denominator_var
        )


class LinearCombinationCalc(CalcProtocol):
    def __init__(
        self,
        *,
        vars: list[str],
        coefficients: list[float] | None = None,
        offset: float = 0.0,
        output_dtype: DataType = DataType.FLOAT,
    ):
        self.vars = vars
        if coefficients is None:
            coefficients = [1.0 for _ in vars]
        if len(vars) != len(coefficients):
            raise ValueError("Number of var names and coefficients must match")
        self.coefficients = coefficients
        self.offset = offset
        self.output_dtype = output_dtype

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return (
            sum(
                coef * select(dataset, var)
                for var, coef in zip(self.vars, self.coefficients)
            )
            + self.offset
        )

    def expected_inputs(self) -> list[str]:
        return self.vars


@domain_calc(performance_ratio)
class PerformanceRatioCalc(CalcBase):
    energy_var: str
    power_capacity_var: str
    insolation_poa_var: str
    combiner_model: CoordCombinerModel
    reference_irradiance: float = REFERENCE_IRRADIANCE

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return performance_ratio(
            energy=select(dataset, self.energy_var),
            power_capacity=select(dataset, self.power_capacity_var),
            insolation_poa=select(dataset, self.insolation_poa_var),
            reference_irradiance=self.reference_irradiance,
            combiner=coord_combiner(self.combiner_model, context),
        )


@calc
class FilterToCalc(CalcBase):
    var: str
    filter_var: str

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return select(dataset, self.var).where(select(dataset, self.filter_var))


@calc
class WithinDeviationCalc(CalcBase):
    var: str
    reference_var: str
    threshold: float
    output_dtype: DataType = DataType.BOOL

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return select(dataset, self.var).where(
            select(dataset, self.reference_var).abs() <= self.threshold
        )


@domain_calc(weighted_average)
class WeightedAverageCalc(CalcBase):
    array_var: str
    weights_var: str
    min_count: int = 1

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return weighted_average(
            array=select(dataset, self.array_var),
            weights=select(dataset, self.weights_var),
            min_count=self.min_count,
        )


@domain_calc(filter_by_capacity)
class FilterByCapacityCalc(CalcBase):
    data_var: str
    capacity_var: str | None = None
    min_capacity_factor: float = 0.0
    max_capacity_factor: float = 1.0

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return filter_by_capacity(
            data=select(dataset, self.data_var),
            capacity=optional(dataset, self.capacity_var),
            min_capacity_factor=self.min_capacity_factor,
            max_capacity_factor=self.max_capacity_factor,
        )


@domain_calc(dc_field_health)
class DcFieldHealthCalc(CalcBase):
    current_combiner_var: str
    power_capacity_dc_combiner_var: str
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return dc_field_health(
            current_combiner=select(dataset, self.current_combiner_var),
            power_capacity_dc_combiner=select(
                dataset, self.power_capacity_dc_combiner_var
            ),
            time_zone=context.project.time_zone,
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(daily_average_c_rate)
class DailyAverageCRateCalc(CalcBase):
    daily_energy_charged_var: str
    daily_energy_discharged_var: str
    energy_capacity_var: str

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return daily_average_c_rate(
            daily_energy_charged=select(dataset, self.daily_energy_charged_var),
            daily_energy_discharged=select(dataset, self.daily_energy_discharged_var),
            energy_capacity=select(dataset, self.energy_capacity_var),
        )


@domain_calc(daily_average_c_rate_charging)
class DailyAverageCRateChargingCalc(CalcBase):
    daily_energy_charged_var: str
    energy_capacity_var: str

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return daily_average_c_rate_charging(
            daily_energy_charged=select(dataset, self.daily_energy_charged_var),
            energy_capacity=select(dataset, self.energy_capacity_var),
        )


@domain_calc(average_while_charging)
class AverageWhileChargingCalc(CalcBase):
    x_var: str
    c_rate_var: str
    combiner_model: CoordCombinerModel
    threshold: float = -0.01

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return average_while_charging(
            x=select(dataset, self.x_var),
            c_rate=select(dataset, self.c_rate_var),
            threshold=self.threshold,
            combiner=coord_combiner(self.combiner_model, context),
        )


@domain_calc(average_while_discharging)
class AverageWhileDischargingCalc(CalcBase):
    x_var: str
    c_rate_var: str
    threshold: float = 0.01
    combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return average_while_discharging(
            x=select(dataset, self.x_var),
            c_rate=select(dataset, self.c_rate_var),
            threshold=self.threshold,
            combiner=coord_combiner(self.combiner_model, context),
        )


@domain_calc(mechanical_availability)
class MechanicalAvailabilityCalc(CalcBase):
    power_kw_var: str
    met_station_poa_irradiance_w_m2_var: str
    poa_threshold: float = 90
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return mechanical_availability(
            power_kw=select(dataset, self.power_kw_var),
            met_station_poa_irradiance_w_m2=select(
                dataset, self.met_station_poa_irradiance_w_m2_var
            ),
            poa_threshold=self.poa_threshold,
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(combiner_mechanical_availability)
class CombinerMechanicalAvailabilityCalc(CalcBase):
    pcs_power_kw_var: str
    combiner_current_amps_var: str
    met_station_poa_irradiance_w_m2_var: str
    combiner_current_threshold_amps: float = 10
    irradiance_poa_threshold_w_m2: float = 90
    pcs_power_threshold_kw: float = 5
    combiner_to_pcs_combiner_model: CoordCombinerModel
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return combiner_mechanical_availability(
            pcs_power_kw=select(dataset, self.pcs_power_kw_var),
            combiner_to_pcs_combiner=coord_combiner(
                self.combiner_to_pcs_combiner_model, context
            ),
            combiner_current_amps=select(dataset, self.combiner_current_amps_var),
            met_station_poa_irradiance_w_m2=select(
                dataset, self.met_station_poa_irradiance_w_m2_var
            ),
            combiner_current_threshold_amps=self.combiner_current_threshold_amps,
            irradiance_poa_threshold_w_m2=self.irradiance_poa_threshold_w_m2,
            pcs_power_threshold_kw=self.pcs_power_threshold_kw,
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(bess_string_complete_availability)
class BessStringCompleteAvailabilityCalc(CalcBase):
    bess_string_status_var: str
    bess_bank_status_var: str
    bess_pcs_status_var: str
    string_to_bank_combiner_model: CoordCombinerModel
    string_to_pcs_combiner_model: CoordCombinerModel
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return bess_string_complete_availability(
            bess_string_status=select(dataset, self.bess_string_status_var),
            bess_bank_status=select(dataset, self.bess_bank_status_var),
            string_to_bank_combiner=coord_combiner(
                self.string_to_bank_combiner_model, context
            ),
            bess_pcs_status=select(dataset, self.bess_pcs_status_var),
            string_to_pcs_combiner=coord_combiner(
                self.string_to_pcs_combiner_model, context
            ),
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(tracker_availability)
class TrackerAvailabilityCalc(CalcBase):
    position_var: str
    setpoint_var: str
    time_combiner_model: CoordCombinerModel
    threshold_deg: float = 2.0

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return tracker_availability(
            position=select(dataset, self.position_var),
            setpoint=select(dataset, self.setpoint_var),
            time_combiner=coord_combiner(self.time_combiner_model, context),
            threshold_deg=self.threshold_deg,
        )


@domain_calc(cycle_count_from_soc)
class CycleCountFromSocCalc(CalcBase):
    soc_5m_var: str
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return cycle_count_from_soc(
            soc_5m=select(dataset, self.soc_5m_var),
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(charging_cycles_from_soc)
class ChargingCyclesFromSocCalc(CalcBase):
    soc_5m_var: str
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return charging_cycles_from_soc(
            soc_5m=select(dataset, self.soc_5m_var),
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(discharging_cycles_from_soc)
class DischargingCyclesFromSocCalc(CalcBase):
    soc_5m_var: str
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return discharging_cycles_from_soc(
            soc_5m=select(dataset, self.soc_5m_var),
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(maximum_continuous_discharge)
class MaximumContinuousDischargeCalc(CalcBase):
    energy_discharged_kwh_var: str
    time_combiner_model: CoordCombinerModel
    energy_capacity_kwh_var: str | None = None

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return maximum_continuous_discharge(
            energy_discharged_kwh=select(dataset, self.energy_discharged_kwh_var),
            time_combiner=coord_combiner(self.time_combiner_model, context),
            energy_capacity_kwh=optional(dataset, self.energy_capacity_kwh_var),
        )


@domain_calc(performance_index)
class PerformanceIndexCalc(CalcBase):
    expected_energy_var: str
    actual_energy_var: str
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return performance_index(
            expected_energy=select(dataset, self.expected_energy_var),
            actual_energy=select(dataset, self.actual_energy_var),
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(curtailed_power_from_eem)
class CurtailedPowerFromEemCalc(CalcBase):
    power_setpoint_var: str
    power_actual_var: str
    power_expected_var: str
    threshold: float = 0.98

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return curtailed_power_from_eem(
            power_setpoint=select(dataset, self.power_setpoint_var),
            power_actual=select(dataset, self.power_actual_var),
            power_expected=select(dataset, self.power_expected_var),
            threshold=self.threshold,
        )


@domain_calc(tracker_deviation_from_setpoint)
class TrackerDeviationFromSetpointCalc(CalcBase):
    position_var: str
    setpoint_var: str
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return tracker_deviation_from_setpoint(
            position=select(dataset, self.position_var),
            setpoint=select(dataset, self.setpoint_var),
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(tracker_setpoint_deviation_from_median)
class TrackerSetpointDeviationFromMedianCalc(CalcBase):
    setpoint_var: str
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return tracker_setpoint_deviation_from_median(
            setpoint=select(dataset, self.setpoint_var),
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(solv_period_kwh_produced)
class SolvPeriodKwhProducedCalc(CalcBase):
    project_irradiance_poa_w_m2_5m_var: str
    project_meter_power_kw_5m_var: str
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return solv_period_kwh_produced(
            project_irradiance_poa_w_m2_5m=select(
                dataset, self.project_irradiance_poa_w_m2_5m_var
            ),
            project_meter_power_kw_5m=select(
                dataset, self.project_meter_power_kw_5m_var
            ),
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(solv_period_kwh_lost)
class SolvPeriodKwhLostCalc(CalcBase):
    project_irradiance_poa_w_m2_5m_var: str
    unit_power_ac_kw_5m_var: str
    unit_power_setpoint_kw_5m_var: str
    project_meter_power_kw_5m_var: str
    unit_ac_capacity_kw_var: str
    unit_dc_capacity_kw_var: str
    project_expected_energy_kwh_5m_var: str
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return solv_period_kwh_lost(
            project_irradiance_poa_w_m2_5m=select(
                dataset, self.project_irradiance_poa_w_m2_5m_var
            ),
            unit_power_ac_kw_5m=select(dataset, self.unit_power_ac_kw_5m_var),
            unit_power_setpoint_kw_5m=select(
                dataset, self.unit_power_setpoint_kw_5m_var
            ),
            project_meter_power_kw_5m=select(
                dataset, self.project_meter_power_kw_5m_var
            ),
            unit_ac_capacity_kw=select(dataset, self.unit_ac_capacity_kw_var),
            unit_dc_capacity_kw=select(dataset, self.unit_dc_capacity_kw_var),
            project_expected_energy_kwh_5m=select(
                dataset, self.project_expected_energy_kwh_5m_var
            ),
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_calc(solv_guarantee_availability)
class SolvGuaranteeAvailabilityCalc(CalcBase):
    period_kwh_produced_var: str
    period_kwh_lost_var: str

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return solv_guarantee_availability(
            period_kwh_produced=select(dataset, self.period_kwh_produced_var),
            period_kwh_lost=select(dataset, self.period_kwh_lost_var),
        )


@calc
class TheoreticalPoaIrradianceCalc(CalcBase):
    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return theoretical_poa_irradiance(
            project=context.project,
            start_time_utc=context.start_time_utc(),
            end_time_utc=context.end_time_utc(),
        )


@domain_calc(pv_dc_combiner_module_excess_degradation)
class PvDcCombinerModuleExcessDegradationCalc(CalcBase):
    met_station_irradiance_poa_w_m2_5m_var: str
    project_theoretical_poa_irradiance_w_m2_5m_var: str
    project_meter_power_kw_5m_var: str
    project_poi_limit_kw_var: str
    pv_inverter_ac_power_kw_5m_var: str
    pv_inverter_ac_power_capacity_kw_var: str
    pv_inverter_reactive_power_kvar_5m_var: str
    pv_inverter_module_voltage_v_5m_var: str
    pv_inverter_module_power_kw_5m_var: str
    pv_inverter_module_power_capacity_kw_var: str
    block_tracker_deviation_from_setpoint_deg_d_var: str
    block_tracker_setpoint_deviation_from_median_deg_d_var: str
    pv_dc_combiner_field_health_d_var: str
    pv_dc_combiner_current_amps_5m_var: str
    pv_dc_combiner_expected_energy_kwh_5m_var: str
    daily_combiner_model: CoordCombinerModel
    broadcast_pcs_to_combiner_model: CoordCombinerModel
    broadcast_block_to_combiner_model: CoordCombinerModel
    module_to_pcs_combiner_model: CoordCombinerModel
    final_time_combiner_model: CoordCombinerModel
    pv_inverter_ac_power_setpoint_kw_5m_var: str | None = None
    pv_inverter_voltage_v_5m_var: str | None = None
    min_poa: float = 250.0
    max_poa_1d: float = 20.0
    max_poa_std: float = 7.5
    max_poa_std_1d: float = 2.5

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return pv_dc_combiner_module_excess_degradation(
            met_station_irradiance_poa_w_m2_5m=select(
                dataset, self.met_station_irradiance_poa_w_m2_5m_var
            ),
            project_theoretical_poa_irradiance_w_m2_5m=select(
                dataset, self.project_theoretical_poa_irradiance_w_m2_5m_var
            ),
            project_meter_power_kw_5m=select(
                dataset, self.project_meter_power_kw_5m_var
            ),
            project_poi_limit_kw=select(dataset, self.project_poi_limit_kw_var),
            pv_inverter_ac_power_kw_5m=select(
                dataset, self.pv_inverter_ac_power_kw_5m_var
            ),
            pv_inverter_ac_power_capacity_kw=select(
                dataset, self.pv_inverter_ac_power_capacity_kw_var
            ),
            pv_inverter_reactive_power_kvar_5m=select(
                dataset, self.pv_inverter_reactive_power_kvar_5m_var
            ),
            pv_inverter_module_voltage_v_5m=select(
                dataset, self.pv_inverter_module_voltage_v_5m_var
            ),
            pv_inverter_module_power_kw_5m=select(
                dataset, self.pv_inverter_module_power_kw_5m_var
            ),
            pv_inverter_module_power_capacity_kw=select(
                dataset, self.pv_inverter_module_power_capacity_kw_var
            ),
            block_tracker_deviation_from_setpoint_deg_d=select(
                dataset, self.block_tracker_deviation_from_setpoint_deg_d_var
            ),
            block_tracker_setpoint_deviation_from_median_deg_d=select(
                dataset, self.block_tracker_setpoint_deviation_from_median_deg_d_var
            ),
            pv_dc_combiner_field_health_d=select(
                dataset, self.pv_dc_combiner_field_health_d_var
            ),
            pv_dc_combiner_current_amps_5m=select(
                dataset, self.pv_dc_combiner_current_amps_5m_var
            ),
            pv_dc_combiner_expected_energy_kwh_5m=select(
                dataset, self.pv_dc_combiner_expected_energy_kwh_5m_var
            ),
            daily_combiner=coord_combiner(self.daily_combiner_model, context),
            broadcast_pcs_to_combiner=coord_combiner(
                self.broadcast_pcs_to_combiner_model, context
            ),
            broadcast_block_to_combiner=coord_combiner(
                self.broadcast_block_to_combiner_model, context
            ),
            module_to_pcs_combiner=coord_combiner(
                self.module_to_pcs_combiner_model, context
            ),
            final_time_combiner=coord_combiner(self.final_time_combiner_model, context),
            pv_inverter_ac_power_setpoint_kw_5m=optional(
                dataset, self.pv_inverter_ac_power_setpoint_kw_5m_var
            ),
            pv_inverter_voltage_v_5m=optional(
                dataset, self.pv_inverter_voltage_v_5m_var
            ),
            min_poa=self.min_poa,
            max_poa_1d=self.max_poa_1d,
            max_poa_std=self.max_poa_std,
            max_poa_std_1d=self.max_poa_std_1d,
        )


@domain_calc(verify_by_capacity)
class VerifyByCapacityCalc(CalcBase):
    data_var: str
    capacity_var: str | None = None
    min_capacity_factor: float = 0.0
    max_capacity_factor: float = 1.0

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return verify_by_capacity(
            data=select(dataset, self.data_var),
            capacity=optional(dataset, self.capacity_var),
            min_capacity_factor=self.min_capacity_factor,
            max_capacity_factor=self.max_capacity_factor,
        )


@domain_calc(accumulate_energy_then_verify_by_capacity)
class AccumulateEnergyThenVerifyByCapacityCalc(CalcBase):
    data_var: str
    time_combiner_model: CoordCombinerModel
    capacity_var: str | None = None
    min_capacity_factor: float = 0.0
    max_capacity_factor: float = 1.0

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return accumulate_energy_then_verify_by_capacity(
            data=select(dataset, self.data_var),
            time_combiner=coord_combiner(self.time_combiner_model, context),
            capacity=optional(dataset, self.capacity_var),
            min_capacity_factor=self.min_capacity_factor,
            max_capacity_factor=self.max_capacity_factor,
        )


@domain_calc(accumulate_energy_then_filter_by_capacity)
class AccumulateEnergyThenFilterByCapacityCalc(CalcBase):
    data_var: str
    time_combiner_model: CoordCombinerModel
    capacity_var: str | None = None
    min_capacity_factor: float = 0.0
    max_capacity_factor: float = 1.0

    def __call__(self, *, dataset: xr.Dataset, context: ContextModel):
        return accumulate_energy_then_filter_by_capacity(
            data=select(dataset, self.data_var),
            time_combiner=coord_combiner(self.time_combiner_model, context),
            capacity=optional(dataset, self.capacity_var),
            min_capacity_factor=self.min_capacity_factor,
            max_capacity_factor=self.max_capacity_factor,
        )
