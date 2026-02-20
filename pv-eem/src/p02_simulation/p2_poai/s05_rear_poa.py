from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

# Assuming these interface classes are defined elsewhere as in the original code
from interfaces import (
    Indeces,
    MetTimeSeries,
    ModuleEquipmentSeries,
    RackingEquipmentSeries,
    StringMetTimeSeries,
    SystemSeries,
    TimeSeries,
)
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p2_poai.rear_poa_models.infinite_sheds import (
    calculate_rear_irradiance_infinite_sheds,
)
from p02_simulation.p2_poai.rear_poa_models.solar_factors import (
    calculate_rear_irradiance_solar_factors,
)


class ModelRearPOA(StrEnum):
    """ModelRearPOA."""

    INFINITE_SHEDS = "infinite_sheds"
    SOLAR_FACTORS = "solar_factors"


@dataclass(init=False, slots=True)
class RearPlaneOfArrayIrradiance:
    """Calculates the effective Plane of Array (POA) irradiance components for the
    rear side
    of bifacial modules using the pvlib infinite sheds model.
    """

    rear: StringMetTimeSeries

    def __init__(
        self,
        model_rear_poa: ModelRearPOA,
        indeces: Indeces,
        ALBEDO: float,
        AXIS_AZIMUTH: float,
        apparent_zenith: TimeSeries,
        azimuth: TimeSeries,
        dni_extra: TimeSeries,
        surface_tilt: StringMetTimeSeries,
        surface_azimuth: StringMetTimeSeries,
        ghi: MetTimeSeries,
        dhi: MetTimeSeries,
        dni: MetTimeSeries,
        pitch: SystemSeries,
        racking_controls_gcr: SystemSeries,
        racking_ids_by_string: SystemSeries,
        racking_height: RackingEquipmentSeries,
        module_ids_by_string: SystemSeries,
        module_bifaciality_factor: ModuleEquipmentSeries,
    ):
        """Calculates rear POA by grouping data by unique scalar combinations
        and looping through them, as required by the pvlib function.
        """
        inputs: pd.DataFrame = merge_by_dimension(
            data_series=[
                apparent_zenith,
                azimuth,
                surface_tilt,
                surface_azimuth,
                ghi,
                dhi,
                dni,
                dni_extra,
                pitch,
                racking_ids_by_string,
                racking_height,
                racking_controls_gcr,
                module_ids_by_string,
                module_bifaciality_factor,
            ],
            merge_how=MergeHow.LEFT,
            indeces=indeces,
        )

        # --- Return No Rear Irradiance if No Bifacial Modules ---
        bifacial_inputs: pd.DataFrame = inputs.loc[
            inputs["bifaciality_factor"] > 0.0
        ].copy()

        if bifacial_inputs.empty:
            self.rear = StringMetTimeSeries(
                pd.Series(0.0, index=inputs.index, name="rear")
            )

        # --- Calculate Rear Irradiance on Bifacial Modules ---
        else:
            match model_rear_poa:
                case ModelRearPOA.INFINITE_SHEDS:
                    raise ValueError("""
                        Infinite sheds model from pvlib has serious bugs, see:
                        https://github.com/pvlib/pvlib-python/issues/2541
                    """)
                    poa_rear_series = calculate_rear_irradiance_infinite_sheds(
                        bifacial_inputs=bifacial_inputs,
                        ALBEDO=ALBEDO,
                    )

                case ModelRearPOA.SOLAR_FACTORS:
                    poa_rear_series = calculate_rear_irradiance_solar_factors(
                        bifacial_inputs=bifacial_inputs,
                        ALBEDO=ALBEDO,
                        AXIS_AZIMUTH=AXIS_AZIMUTH,
                    )
                case _:
                    raise ValueError(f"Invalid model_rear_poa: {model_rear_poa}")

            # Create a final series:
            # 0 for non-bifacial and calculated values for bifacial
            final_rear_irradiance = pd.Series(0.0, index=inputs.index, name="rear")
            final_rear_irradiance.update(poa_rear_series)

            self.rear = StringMetTimeSeries(final_rear_irradiance)
