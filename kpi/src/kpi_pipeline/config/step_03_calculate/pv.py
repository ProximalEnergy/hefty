from core.enumerations import DeviceType

from kpi_pipeline.base.enums import Aggregation
from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import CoordCombinerModel
from kpi_pipeline.config.helper_fields import _fill_energy_accumulator
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.services.calc import (
    CalcProcess,
    CurtailedPowerFromEemCalc,
    DiffAndFilterCalc,
    FillNACalc,
    ProcessCalc,
    SelectCalc,
    TheoreticalPoaIrradianceCalc,
)
from kpi_pipeline.services.process import (
    AggregateProcess,
    ScaleOffsetProcess,
)
from kpi_pipeline.services.schema import AddCalculationsSchema


class CalculatePV(AddCalculationsSchema):
    pv_inverter_energy_production_total_filled_kwh_5m = _fill_energy_accumulator(
        Download.time_series.pv_inverter_energy_production_total_kwh_5m.var
    )

    pv_inverter_energy_production_kwh_5m = Field(
        DiffAndFilterCalc(
            energy_total_var=pv_inverter_energy_production_total_filled_kwh_5m.var,
            power_capacity_var=Validate.pv_inverter_ac_capacity_kw.var,
            max_capacity_factor=1 / 12,  # 12 steps per hour
        )
    )

    project_energy_production_kwh_5m = Field(
        CalcProcess(
            calc=SelectCalc(var=Validate.project_active_power_meter_kw_5m.var),
            process=ScaleOffsetProcess(scale=1 / 12),
        )
    )

    pv_inverter_module_energy_kwh_5m = Field(
        CalcProcess(
            calc=SelectCalc(
                var=Download.time_series.pv_inverter_module_power_ac_kw_5m.var
            ),
            process=ScaleOffsetProcess(scale=1 / 12),
        )
    )

    project_irradiance_poa_w_m2_5m = Field(
        CalcProcess(
            calc=SelectCalc(var=Validate.met_station_irradiance_poa_w_m2_5m.var),
            process=AggregateProcess(
                agg=Aggregation.MEAN,
                combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.MET_STATION,
                ),
            ),
        )
    )

    project_insolation_poa_kwh_m2_5m = Field(
        CalcProcess(
            calc=SelectCalc(var=project_irradiance_poa_w_m2_5m.var),
            process=ScaleOffsetProcess(scale=1 / 12),
        )
    )

    # expected energy

    # project

    project_power_expected_best_kw_5m = Field(
        FillNACalc(
            vars=[
                Download.expected_energy.project_power_expected_degraded_soiled_kw_5m.var,
                Download.expected_energy.project_power_expected_degraded_kw_5m.var,
                Download.expected_energy.project_power_expected_soiled_kw_5m.var,
                Download.expected_energy.project_power_expected_kw_5m.var,
            ],
            allow_missing_fields=True,
        )
    )

    project_energy_expected_best_kwh_5m = Field(
        ProcessCalc(
            var=project_power_expected_best_kw_5m.var,
            process=ScaleOffsetProcess(scale=1 / 12),
        )
    )

    # dc combiner

    pv_dc_combiner_power_expected_best_kw_5m = Field(
        FillNACalc(
            vars=[
                Download.expected_energy.pv_dc_combiner_power_expected_degraded_soiled_kw_5m.var,
                Download.expected_energy.pv_dc_combiner_power_expected_degraded_kw_5m.var,
                Download.expected_energy.pv_dc_combiner_power_expected_soiled_kw_5m.var,
                Download.expected_energy.pv_dc_combiner_power_expected_kw_5m.var,
            ],
            allow_missing_fields=True,
        )
    )

    pv_dc_combiner_energy_expected_best_kwh_5m = Field(
        ProcessCalc(
            var=pv_dc_combiner_power_expected_best_kw_5m.var,
            process=ScaleOffsetProcess(scale=1 / 12),
        )
    )

    project_power_curtailed_kw_5m = Field(
        CurtailedPowerFromEemCalc(
            power_setpoint_var=Validate.project_power_setpoint_kw_5m.var,
            power_actual_var=project_energy_production_kwh_5m.var,
            power_expected_var=project_energy_expected_best_kwh_5m.var,
            threshold=0.98,
        )
    )

    project_energy_curtailed_kwh_5m = Field(
        ProcessCalc(
            var=project_power_curtailed_kw_5m.var,
            process=ScaleOffsetProcess(scale=1 / 12),
        )
    )

    # pv lib integration

    project_theoretical_poa_irradiance_w_m2_5m = Field(TheoreticalPoaIrradianceCalc())
