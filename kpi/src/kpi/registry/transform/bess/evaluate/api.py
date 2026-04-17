import xarray as xr
from core.enumerations import DeviceType
from kpi.base.protocol import CalcProtocol
from kpi.domain.bess import resting_soc
from kpi.domain.util import TimeCoords, coord, fill_accumulator
from kpi.op.field import MakeField
from kpi.op.time import DateLocal5m
from kpi.op.transform.class_calc import Energy5mFromAccumulator
from kpi.op.transform.method import Input, method_calc
from kpi.op.transform.schema import CalcSchema
from kpi.op.transform.unary import unary_field
from kpi.registry.download.sensor.bess import DownloadSensorBess
from kpi.registry.transform.bess.clean.api import TransformBessClean as Clean

field = MakeField[CalcProtocol].infer_doc


class TransformBessEvaluate(CalcSchema):
    date_local_5m = field(DateLocal5m())

    # =======================================================
    # Backfill and forward fill accumulators to remove nans
    # =======================================================

    # project level

    project_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.project_total_energy_charged_raw_kwh_5m,
    )

    project_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.project_total_energy_discharged_raw_kwh_5m,
    )

    project_total_aux_energy_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.project_total_aux_energy_raw_kwh_5m,
    )

    # mv circuit level

    circuit_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.circuit_total_energy_charged_raw_kwh_5m,
    )

    circuit_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.circuit_total_energy_discharged_raw_kwh_5m,
    )

    # pcs level

    pcs_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.pcs_total_energy_charged_raw_kwh_5m,
    )

    pcs_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.pcs_total_energy_discharged_raw_kwh_5m,
    )

    # pcs module level

    pcs_module_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.pcs_module_total_energy_charged_raw_kwh_5m,
    )

    pcs_module_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.pcs_module_total_energy_discharged_raw_kwh_5m,
    )

    # string level

    string_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.string_total_energy_charged_raw_kwh_5m,
    )

    string_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.string_total_energy_discharged_raw_kwh_5m,
    )

    # =======================================================
    # Estimate 5-minute energy
    # =======================================================

    # Project level

    project_energy_charged_kwh_5m = field(
        Energy5mFromAccumulator(
            accumulator=project_total_energy_charged_filled_kwh_5m.name,
            power_capacity=Clean.project_power_capacity_kw.name,
        )
    )

    project_energy_discharged_kwh_5m = field(
        Energy5mFromAccumulator(
            accumulator=project_total_energy_discharged_filled_kwh_5m.name,
            power_capacity=Clean.project_power_capacity_kw.name,
        )
    )

    # PCS level

    pcs_energy_charged_dc_kwh_5m = field(
        Energy5mFromAccumulator(
            accumulator=pcs_total_energy_charged_filled_kwh_5m.name,
            power_capacity=Clean.pcs_power_capacity_kw.name,
        )
    )

    pcs_energy_discharged_dc_kwh_5m = field(
        Energy5mFromAccumulator(
            accumulator=pcs_total_energy_discharged_filled_kwh_5m.name,
            power_capacity=Clean.pcs_power_capacity_kw.name,
        )
    )

    # =======================================================
    # C-Rate
    # =======================================================

    # project level

    @method_calc
    def project_c_rate_5m(
        power: xr.DataArray = Input(Clean.bess_project_power_kw_5m),
        energy_capacity: xr.DataArray = Input(Clean.project_energy_capacity_kwh),
    ) -> xr.DataArray:
        return power / energy_capacity

    # pcs level

    @method_calc
    def pcs_c_rate_5m(
        power: xr.DataArray = Input(Clean.pcs_power_kw_5m),
        energy_capacity: xr.DataArray = Input(Clean.pcs_energy_capacity_kwh),
    ) -> xr.DataArray:
        return power / energy_capacity

    # string level

    @method_calc
    def string_c_rate_5m(
        power: xr.DataArray = Input(Clean.string_power_kw_5m),
        energy_capacity: xr.DataArray = Input(Clean.string_energy_capacity_kwh),
    ) -> xr.DataArray:
        return power / energy_capacity

    # =======================================================
    # Resting SOC
    # =======================================================

    # project level
    project_resting_soc_5m = unary_field(
        resting_soc,
        field=Clean.project_soc_5m,
    )

    # bank level

    bank_resting_soc_5m = unary_field(
        resting_soc,
        field=Clean.bank_soc_5m,
    )

    # block level

    block_resting_soc_5m = unary_field(
        resting_soc,
        field=Clean.block_soc_5m,
    )

    # string level

    string_resting_soc_5m = unary_field(
        resting_soc,
        field=Clean.string_soc_5m,
    )

    # =======================================================
    # Other
    # =======================================================

    @method_calc
    def project_soh_5m(
        soh: xr.DataArray = Input(Clean.string_soh_5m),
    ) -> xr.DataArray:
        """
        Project SOH Per 5-Minute Interval
        average across all string devices for each 5-minute interval.
        String devices with missing SOH are excluded from the average.
        """
        return soh.mean(dim=coord(DeviceType.BESS_STRING))

    # =======================================================
    # Availability
    # =======================================================

    @method_calc
    def pcs_offline_event_5m(
        offline_event_change: xr.DataArray = Input(Clean.pcs_offline_event_change_5m),
    ) -> xr.DataArray:
        """
        PCS Offline Event Per 5-Minute Interval
        """
        return offline_event_change.cumsum(dim=TimeCoords.TIME_5MIN_UTC.value) > 0

    @method_calc
    def pcs_module_offline_event_5m(
        offline_event_change: xr.DataArray = Input(
            Clean.pcs_module_offline_event_change_5m
        ),
    ) -> xr.DataArray:
        """
        PCS Module Offline Event Per 5-Minute Interval
        """
        return offline_event_change.cumsum(dim=TimeCoords.TIME_5MIN_UTC.value) > 0

    @method_calc
    def pcs_availability_5m(
        offline_event: xr.DataArray = Input(pcs_offline_event_5m),
    ) -> xr.DataArray:
        """
        PCS Availability Per 5-Minute Interval
        1 - `offline_event`
        """
        return 1 - offline_event

    @method_calc
    def project_pcs_availability_5m(
        availability: xr.DataArray = Input(pcs_availability_5m),
    ) -> xr.DataArray:
        """
        Project PCS Availability Per 5-Minute Interval
        average across all PCS devices for each 5-minute interval.
        """
        return availability.mean(dim=coord(DeviceType.BESS_PCS))

    @method_calc
    def project_energy_availability_5m(
        availability: xr.DataArray = Input(project_pcs_availability_5m),
        soh: xr.DataArray = Input(project_soh_5m),
        energy_capacity: xr.DataArray = Input(Clean.project_energy_capacity_kwh),
    ) -> xr.DataArray:
        """
        Project Energy Availability Per 5-Minute Interval
        system availability multiplied by project SOH and energy capacity.
        """
        return availability * soh * energy_capacity

    @method_calc
    def project_power_availability_5m(
        availability: xr.DataArray = Input(project_pcs_availability_5m),
        power_capacity: xr.DataArray = Input(Clean.project_power_capacity_kw),
        poi_capacity: xr.DataArray = Input(Clean.project_poi_limit_kw),
    ) -> xr.DataArray:
        """
        Project Power Availability Per 5-Minute Interval
        availability times power capacity, clipped at POI capacity
        """
        return (availability * power_capacity).clip(max=poi_capacity)
