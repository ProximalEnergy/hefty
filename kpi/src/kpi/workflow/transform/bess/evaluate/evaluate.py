import xarray as xr
from kpi.domain.bess import resting_soc
from kpi.domain.util import diff, fill_accumulator, filter_mask
from kpi.service.field import Field
from kpi.service.time import DayGrouper
from kpi.service.transform.method import Input, method_calc
from kpi.service.transform.schema import CalcSchema
from kpi.service.transform.unary import unary_field
from kpi.workflow.download.sensor.bess import DownloadSensorBess
from kpi.workflow.transform.bess.clean.workflow import TransformBessClean as Clean


class TransformBessEvaluate(CalcSchema):
    date_local_5m = Field(DayGrouper())

    # =======================================================
    # Backfill and forward fill accumulators to remove nans
    # =======================================================

    # project level

    project_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        DownloadSensorBess.project_total_energy_charged_raw_kwh_5m.name,
    )

    project_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        DownloadSensorBess.project_total_energy_discharged_raw_kwh_5m.name,
    )

    project_total_aux_energy_filled_kwh_5m = unary_field(
        fill_accumulator,
        DownloadSensorBess.project_total_aux_energy_raw_kwh_5m.name,
    )

    # mv circuit level

    circuit_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        DownloadSensorBess.circuit_total_energy_charged_raw_kwh_5m.name,
    )

    circuit_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        DownloadSensorBess.circuit_total_energy_discharged_raw_kwh_5m.name,
    )

    # pcs level

    pcs_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        DownloadSensorBess.pcs_total_energy_charged_raw_kwh_5m.name,
    )

    pcs_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        DownloadSensorBess.pcs_total_energy_discharged_raw_kwh_5m.name,
    )

    # pcs module level

    pcs_module_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        DownloadSensorBess.pcs_module_total_energy_charged_raw_kwh_5m.name,
    )

    pcs_module_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        DownloadSensorBess.pcs_module_total_energy_discharged_raw_kwh_5m.name,
    )

    # string level

    string_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        DownloadSensorBess.string_total_energy_charged_raw_kwh_5m.name,
    )

    string_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        DownloadSensorBess.string_total_energy_discharged_raw_kwh_5m.name,
    )

    # =======================================================
    # Estimate 5-minute energy
    # =======================================================

    @method_calc
    def project_energy_charged_kwh_5m(
        energy_total: xr.DataArray = Input(
            project_total_energy_charged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.project_power_capacity_kw.name),
    ) -> xr.DataArray:
        difference = diff(energy_total)
        epsilon = 1e-6
        clean_diff = difference.where(
            filter_mask(
                filter_by=difference / power_capacity,
                min_value=-epsilon,
                max_value=1 / 12 + epsilon,
            )
        )
        return clean_diff

    @method_calc
    def project_energy_discharged_kwh_5m(
        energy_total: xr.DataArray = Input(
            project_total_energy_discharged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.project_power_capacity_kw.name),
    ) -> xr.DataArray:
        difference = diff(energy_total)
        epsilon = 1e-6
        clean_diff = difference.where(
            filter_mask(
                filter_by=difference / power_capacity,
                min_value=-epsilon,
                max_value=1 / 12 + epsilon,
            )
        )
        return clean_diff

    # =======================================================
    # C-Rate
    # =======================================================

    # project level

    @method_calc
    def project_c_rate_5m(
        power: xr.DataArray = Input(Clean.project_power_kw_5m.name),
        energy_capacity: xr.DataArray = Input(Clean.project_energy_capacity_kwh.name),
    ) -> xr.DataArray:
        return power / energy_capacity

    # pcs level

    @method_calc
    def pcs_c_rate_5m(
        power: xr.DataArray = Input(Clean.pcs_power_kw_5m.name),
        energy_capacity: xr.DataArray = Input(Clean.pcs_energy_capacity_kwh.name),
    ) -> xr.DataArray:
        return power / energy_capacity

    # string level

    @method_calc
    def string_c_rate_5m(
        power: xr.DataArray = Input(Clean.string_power_kw_5m.name),
        energy_capacity: xr.DataArray = Input(Clean.string_energy_capacity_kwh.name),
    ) -> xr.DataArray:
        return power / energy_capacity

    # =======================================================
    # Resting SOC
    # =======================================================

    # project level
    project_resting_soc_5m = unary_field(
        resting_soc,
        Clean.project_soc_5m.name,
    )

    # bank level

    bank_resting_soc_5m = unary_field(
        resting_soc,
        Clean.bank_soc_5m.name,
    )

    # block level

    block_resting_soc_5m = unary_field(
        resting_soc,
        Clean.block_soc_5m.name,
    )

    # string level

    string_resting_soc_5m = unary_field(
        resting_soc,
        Clean.string_soc_5m.name,
    )
