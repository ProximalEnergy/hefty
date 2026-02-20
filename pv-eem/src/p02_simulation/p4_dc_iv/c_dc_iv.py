from dataclasses import dataclass

import pandas as pd
from interfaces import (
    CombinerDeviceSeries,
    CombinerTimeSeries,
    Indeces,
    MetTimeSeries,
    QualityAssurance,
    StringMetTimeSeries,
    SystemSeries,
)
from p01_get_data.source_proximal.s09_get_module_data import Module
from p02_simulation.p4_dc_iv.s01_cell_temp import CellTemperature, ModelThermal
from p02_simulation.p4_dc_iv.s02_single_diode_params import (
    ModelSingleDiode,
    SingleDiodeParameters,
)
from p02_simulation.p4_dc_iv.s02b_pv_watts_dc import PVWattsModel
from p02_simulation.p4_dc_iv.s03_iv_1_module import SingleDiodeModel
from p02_simulation.p4_dc_iv.s04_iv_2_warranted_degradation import (
    IVafterDegradation,
    ModelDegradation,
)
from p02_simulation.p4_dc_iv.s05_iv_3_string import StringIVCurve
from p02_simulation.p4_dc_iv.s06_iv_4_dc_wiring_to_combiner import (
    IVafterDCWiring,
    ModelDCWiringToCombiner,
)
from p02_simulation.p4_dc_iv.s07_iv_combiner import IVatCombiner
from p02_simulation.p4_dc_iv.s08_iv_qc import IVafterQC


@dataclass(init=False, slots=True)
class PowerAtCombiner:
    """PowerAtCombiner."""

    time: CombinerTimeSeries
    device_ids: CombinerTimeSeries
    p_mp: CombinerTimeSeries
    v_mp: CombinerTimeSeries
    i_mp: CombinerTimeSeries
    v_oc: CombinerTimeSeries
    i_sc: CombinerTimeSeries
    tier: CombinerTimeSeries
    tier_codes: CombinerTimeSeries

    # pass through for later calculation
    _i_mp_array_stc: CombinerTimeSeries
    _dc_line_to_inverter_stc: CombinerTimeSeries

    def __init__(
        self,
        *,
        single_diode_model: ModelSingleDiode,
        degradation_model: ModelDegradation,
        dc_wiring_to_combiner_model: ModelDCWiringToCombiner,
        indeces: Indeces,
        modules: Module,
        egpoai: StringMetTimeSeries,
        temperature_ambient: MetTimeSeries,
        module_id_by_string: SystemSeries,
        modules_per_string: SystemSeries,
        combiner_device_id: SystemSeries | CombinerDeviceSeries,
        strings_per_combiner: SystemSeries,
        dc_line_to_combiner_stc: SystemSeries,
        dc_line_to_inverter_stc: SystemSeries,
        cod: str,
        quality_assurance: QualityAssurance,
    ):
        # --- Calculations ---
        cell_temperature = CellTemperature(
            cell_temperature_model=ModelThermal.PVSYST_CELL,
            indeces=indeces,
            egpoai=egpoai,
            temperature_ambient=temperature_ambient,
            module_id_by_string=module_id_by_string,
            module_efficiency=modules.efficiency,
        )
        iv_curve: PVWattsModel | SingleDiodeModel | None = None
        match single_diode_model:
            case ModelSingleDiode.PVWATTS:
                iv_curve = PVWattsModel(
                    indeces=indeces,
                    module_id_by_string=module_id_by_string,
                    modules=modules,
                    cell_temperature=cell_temperature.cell_temperature,
                    egpoai=egpoai,
                )
            case ModelSingleDiode.DESOTO:
                single_diode_inputs = SingleDiodeParameters(
                    single_diode_model=single_diode_model,
                    indeces=indeces,
                    egpoai=egpoai,
                    cell_temperature=cell_temperature.cell_temperature,
                    module_id_by_string=module_id_by_string,
                    modules=modules,
                )

                iv_curve = SingleDiodeModel(
                    indeces=indeces,
                    single_diode_parameters=single_diode_inputs,
                )
            case _:
                raise ValueError(
                    f"Unsupported single diode model: {single_diode_model}"
                )

        iv_degradation = IVafterDegradation(
            model=degradation_model,
            indeces=indeces,
            module_id_by_string=module_id_by_string,
            modules=modules,
            cod=cod,
            iv_curve=iv_curve,
        )

        test = pd.concat(
            [
                indeces.string_met_time_index.time,
                indeces.string_met_time_index.string_id,
                iv_curve.i_mp,
            ],
            axis=1,
        )
        _df = test[test["string_id"] == 250]
        iv_at_string = StringIVCurve(
            indeces=indeces,
            modules_per_string=modules_per_string,
            iv_after_degradation=iv_degradation,
        )

        # # Plot iv_at_string for string_id = 0
        # string_index = indeces.string_met_time_index
        # string_filtered = string_index[string_index["string_id"] == 0]

        # v_mp_data = iv_at_string.v_mp.loc[string_filtered.index]
        # i_mp_data = iv_at_string.i_mp.loc[string_filtered.index]
        # p_mp_data = v_mp_data * i_mp_data

        # plt.figure(figsize=(10, 6))
        # plt.plot(string_filtered["time"], p_mp_data)
        # plt.title("Power at Max Power Point for String ID 0")
        # plt.xlabel("Time")
        # plt.ylabel("P_mp (W)")
        # plt.grid(True)
        # plt.show()

        iv_after_wiring = IVafterDCWiring(
            model=dc_wiring_to_combiner_model,
            indeces=indeces,
            modules_per_string=modules_per_string,
            dc_line_to_combiner_stc=dc_line_to_combiner_stc,
            module_id_by_string=module_id_by_string,
            string_iv_curve=iv_at_string,
            imp_module_STC=modules.imp,
            vmp_module_STC=modules.vmp,
        )

        iv_at_combiner = IVatCombiner(
            indeces=indeces,
            quality_assurance=quality_assurance,
            iv_after_wiring=iv_after_wiring,
            combiner_device_id=combiner_device_id,
            strings_per_combiner=strings_per_combiner,
            module_id_by_string=module_id_by_string,
            module_i_mp_stc=modules.imp,
            dc_line_to_inverter_stc=dc_line_to_inverter_stc,
        )

        iv_after_qc = IVafterQC(
            iv_at_combiner=iv_at_combiner,
        )

        # --- Assignments ---
        self.time = CombinerTimeSeries(indeces.combiner_time_index.loc[:, "time"])
        self.device_ids = CombinerTimeSeries(
            indeces.combiner_time_index.loc[:, "combiner_device_id"]
        )

        # Set the final IV characteristics
        self.p_mp = iv_after_qc.p_mp
        self.v_mp = iv_after_qc.v_mp
        self.i_mp = iv_after_qc.i_mp
        self.v_oc = iv_after_qc.v_oc
        self.i_sc = iv_after_qc.i_sc

        # re-map to new types since we aggregated to a new index
        combiner_device_id = CombinerDeviceSeries(combiner_device_id)
        self.tier = CombinerTimeSeries(iv_after_qc.tier)
        self.tier_codes = CombinerTimeSeries(iv_after_qc.tier_codes)

        # pass through for later calculation
        self._i_mp_array_stc = iv_after_qc._i_mp_array_stc
        self._dc_line_to_inverter_stc = iv_after_qc._dc_line_to_inverter_stc
