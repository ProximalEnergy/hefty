from core.enumerations import DeviceType

import kpi_pipeline.services.calc as calc
import kpi_pipeline.services.process as process
from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import CoordCombinerModel
from kpi_pipeline.config.helper_fields import _5min_to_daily
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_03_calculate import Calculate
from kpi_pipeline.services.schema import AddCalculationsSchema


class AggregateBESSAvailability(AddCalculationsSchema):
    bess_bank_availability_d = Field(
        calc.ProcessCalc(
            var=Download.status.bess_bank_status_5m.var,
            process=process.ProcessList(
                steps=[
                    process.AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(),
                    ),
                    process.FilterToRangeProcess(
                        min_value=0,
                        max_value=1,
                    ),
                ],
            ),
        )
    )

    project_bess_bank_availability_d = Field(
        calc.ProcessCalc(
            var=Download.status.bess_bank_status_5m.var,
            process=process.ProcessList(
                steps=[
                    process.AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(
                            child_device_axis=DeviceType.BESS_BANK,
                        ),
                    ),
                    process.FilterToRangeProcess(
                        min_value=0,
                        max_value=1,
                    ),
                ],
            ),
        )
    )

    bess_pcs_availability_d = Field(
        calc.ProcessCalc(
            var=Download.status.bess_pcs_status_5m.var,
            process=process.ProcessList(
                steps=[
                    process.AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(),
                    ),
                    process.FilterToRangeProcess(
                        min_value=0,
                        max_value=1,
                    ),
                ],
            ),
        )
    )

    project_bess_pcs_availability_d = Field(
        calc.ProcessCalc(
            var=Download.status.bess_pcs_status_5m.var,
            process=process.ProcessList(
                steps=[
                    process.AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(
                            child_device_axis=DeviceType.BESS_PCS,
                        ),
                    ),
                    process.FilterToRangeProcess(
                        min_value=0,
                        max_value=1,
                    ),
                ],
            ),
        )
    )

    bess_pcs_module_availability_d = Field(
        calc.ProcessCalc(
            var=Calculate.bess_pcs_module_is_offline_5m.var,
            process=process.ProcessList(
                steps=[
                    process.AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(),
                    ),
                ],
            ),
        )
    )

    project_bess_pcs_module_availability_d = Field(
        calc.ProcessCalc(
            var=Calculate.bess_pcs_module_is_offline_5m.var,
            process=process.ProcessList(
                steps=[
                    process.AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(
                            child_device_axis=DeviceType.BESS_PCS_MODULE,
                        ),
                    ),
                    process.FilterToRangeProcess(
                        min_value=0,
                        max_value=1,
                    ),
                ],
            ),
        )
    )

    bess_string_complete_availability_d = Field(
        calc.CalcProcess(
            calc=calc.BessStringCompleteAvailabilityCalc(
                bess_string_status_var=Download.status.bess_string_status_5m.var,
                bess_bank_status_var=Download.status.bess_bank_status_5m.var,
                bess_pcs_status_var=Download.status.bess_pcs_status_5m.var,
                string_to_bank_combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.BESS_STRING,
                    parent_device_axis=DeviceType.BESS_BANK,
                ),
                string_to_pcs_combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.BESS_STRING,
                    parent_device_axis=DeviceType.BESS_PCS,
                ),
                time_combiner_model=_5min_to_daily(),
            ),
            process=process.FilterToRangeProcess(
                min_value=0,
                max_value=1,
            ),
        )
    )

    project_complete_availability_d = Field(
        calc.CalcProcess(
            calc=calc.BessStringCompleteAvailabilityCalc(
                bess_string_status_var=Download.status.bess_string_status_5m.var,
                bess_bank_status_var=Download.status.bess_bank_status_5m.var,
                bess_pcs_status_var=Download.status.bess_pcs_status_5m.var,
                string_to_bank_combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.BESS_STRING,
                    parent_device_axis=DeviceType.BESS_BANK,
                ),
                string_to_pcs_combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.BESS_STRING,
                    parent_device_axis=DeviceType.BESS_PCS,
                ),
                time_combiner_model=_5min_to_daily(
                    child_device_axis=DeviceType.BESS_STRING,
                ),
            ),
            process=process.FilterToRangeProcess(
                min_value=0,
                max_value=1,
            ),
        )
    )
