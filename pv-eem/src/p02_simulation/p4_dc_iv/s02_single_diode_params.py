from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
import pvlib
from interfaces import Indeces, StringMetTimeSeries, SystemSeries
from p01_get_data.source_proximal.s09_get_module_data import Module
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.data_factorizer import factorize


class ModelSingleDiode(StrEnum):
    """ModelSingleDiode."""

    PVWATTS = "PVWATTS"
    DESOTO = "DESOTO"
    PVSYST = "PVSYST"

    def __eq__(self, other):
        """Robust equality comparison that works with module reloading."""
        if isinstance(other, str):
            return self.value == other
        if hasattr(other, "value"):
            return self.value == other.value
        if hasattr(other, "name"):
            return self.name == other.name
        return super().__eq__(other)

    def __hash__(self):
        """Ensure hash consistency for value-based equality."""
        return hash(self.value)

    @classmethod
    def safe_compare(cls, enum_instance, target_value):
        """Safe comparison method for enum instances that handles module reloading.

        Args:
            enum_instance: The enum instance to compare
            target_value: Can be an enum instance, string value, or enum name

        Returns:
            bool: True if the values match, False otherwise
        """
        if isinstance(target_value, str):
            # Compare by string value
            return enum_instance.value == target_value
        elif hasattr(target_value, "value"):
            # Compare by enum value
            return enum_instance.value == target_value.value
        elif hasattr(target_value, "name"):
            # Compare by enum name
            return enum_instance.name == target_value.name
        return False

    @classmethod
    def from_value(cls, value):
        """Create enum instance from value, handling string inputs.

        Args:
            value: String value or existing enum instance

        Returns:
            ModelSingleDiode: The corresponding enum instance
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            for member in cls:
                if member.value == value:
                    return member
            raise ValueError(f"No {cls.__name__} member with value '{value}'")
        raise TypeError(f"Cannot convert {type(value)} to {cls.__name__}")


@dataclass(init=False, slots=True)
class SingleDiodeParameters:
    """SingleDiodeParameters."""

    pv_watts_power: StringMetTimeSeries
    photocurrent: StringMetTimeSeries
    saturation_current: StringMetTimeSeries
    resistance_series: StringMetTimeSeries
    resistance_shunt: StringMetTimeSeries
    nNsVth: StringMetTimeSeries
    _unique_ids: StringMetTimeSeries

    def __init__(
        self,
        *,
        single_diode_model: ModelSingleDiode,
        indeces: Indeces,
        module_id_by_string: SystemSeries,
        modules: Module,
        cell_temperature: StringMetTimeSeries,
        egpoai: StringMetTimeSeries,
    ):
        # --- CONSTANTS ---
        IRRAD_REF = 1000.0  # W/m2
        TEMP_REF = 25.0  # C

        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                module_id_by_string,
                modules.pmax,
                modules.photocurrent,
                modules.alpha_isc,
                modules.modified_ideality_factor,
                modules.diode_saturation_current,
                modules.r_series,
                modules.r_shunt,
                modules.eg,
                modules.degdt,
                cell_temperature,
                egpoai,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # Module data at reference conditions
        inputs = inputs.rename(
            columns={
                "alpha_isc": "alpha_isc_ref",
                "modified_ideality_factor": "modified_ideality_factor_ref",
                "photocurrent": "photocurrent_ref",
                "diode_saturation_current": "diode_saturation_current_ref",
                "r_series": "r_series_ref",
                "r_shunt": "r_shunt_ref",
                "eg": "eg_ref",
                "degdt": "degdt_ref",
            }
        )

        # --- FACTORIZE ---
        # Many of the parameters are unique to the pv_module_id
        inputs = factorize(
            dataframe=inputs,
            columns=["module_equipment_id", "global", "cell_temp"],
            rounding_precision=1,
        )

        unique_by_group = inputs.groupby("_unique_id").first()
        unique_by_group = unique_by_group.reset_index()

        # --- Function ---
        match single_diode_model:
            case ModelSingleDiode.DESOTO:
                params_raw = pvlib.pvsystem.calcparams_desoto(
                    effective_irradiance=unique_by_group["global"],
                    temp_cell=unique_by_group["cell_temp"],
                    alpha_sc=unique_by_group["alpha_isc_ref"],
                    a_ref=unique_by_group["modified_ideality_factor_ref"],
                    I_L_ref=unique_by_group["photocurrent_ref"],
                    I_o_ref=unique_by_group["diode_saturation_current_ref"],
                    R_sh_ref=unique_by_group["r_shunt_ref"],
                    R_s=unique_by_group["r_series_ref"],
                    EgRef=unique_by_group["eg_ref"],
                    dEgdT=unique_by_group["degdt_ref"],
                    irrad_ref=IRRAD_REF,
                    temp_ref=TEMP_REF,
                )

            # case ModelSingleDiode.PVSYST:
            #     params_raw = pvlib.pvsystem.calcparams_pvsyst(
            #         effective_irradiance=unique_by_group["global"],
            #         temp_cell=unique_by_group["cell_temp"],
            #         alpha_sc=unique_by_group["alpha_isc_ref"],
            #         gamma_ref=unique_by_group["gamma_ref"],
            #         mu_gamma=unique_by_group["mu_gamma"],
            #         I_L_ref=unique_by_group["photocurrent_ref"],
            #         I_o_ref=unique_by_group["diode_saturation_current_ref"],
            #         R_sh_ref=unique_by_group["R_sh_ref"],
            #         R_sh_0=unique_by_group["R_sh_0"],
            #         R_s=unique_by_group["R_s"],
            #         cells_in_series=unique_by_group["cells_in_series"],
            #         R_sh_exp=unique_by_group["R_sh_exp"],  # type: ignore
            #         EgRef=unique_by_group["EgRef"],  # type: ignore
            #         irrad_ref=IRRAD_REF,  # type: ignore
            #         temp_ref=TEMP_REF,  # type: ignore
            #     )
            case _:
                raise ValueError(
                    f"Unsupported single diode model: {single_diode_model}"
                )

        # --- MERGE ---
        params_renamed = pd.DataFrame(
            {
                "_unique_id": unique_by_group["_unique_id"],
                "photocurrent": params_raw[0],
                "saturation_current": params_raw[1],
                "resistance_series": params_raw[2],
                "resistance_shunt": params_raw[3],
                "nNsVth": params_raw[4],
            }
        )
        outputs = pd.merge(
            left=inputs,
            right=params_renamed,
            on="_unique_id",
            how="left",
        )

        self.photocurrent = StringMetTimeSeries(outputs.loc[:, "photocurrent"])
        self.saturation_current = StringMetTimeSeries(
            outputs.loc[:, "saturation_current"]
        )
        self.resistance_series = StringMetTimeSeries(
            outputs.loc[:, "resistance_series"]
        )
        self.resistance_shunt = StringMetTimeSeries(outputs.loc[:, "resistance_shunt"])
        self.nNsVth = StringMetTimeSeries(outputs.loc[:, "nNsVth"])
        self._unique_ids = StringMetTimeSeries(outputs.loc[:, "_unique_id"])
