import warnings
from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
import pvlib
from interfaces import (
    Indeces,
    MetTimeSeries,
    StringMetTimeSeries,
    TimeSeries,
)
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.known_exception import (
    KnownException,
    KnownExceptionType,
)


class ModelRetroTransposition(StrEnum):
    """ModelRetroTransposition."""

    GTI_DIRINT = "gti_dirint"


@dataclass(init=False, slots=True)
class HorizontalIrradianceRetro:
    """HorizontalIrradianceRetro."""

    ghi_retro: MetTimeSeries
    dni_retro: MetTimeSeries
    dhi_retro: MetTimeSeries

    def __init__(
        self,
        model: ModelRetroTransposition,
        indeces: Indeces,
        surface_tilt: StringMetTimeSeries,
        surface_azimuth: StringMetTimeSeries,
        aoi: StringMetTimeSeries,
        poa: MetTimeSeries,
        solar_azimuth: TimeSeries,
        solar_zenith: TimeSeries,
        temp_dew: MetTimeSeries,
        site_pressure: float,
        ALBEDO: float,
    ):
        """Calculate the plane of array irradiance (sky_diffuse)
        via retro-transposition.  gti_dirint model does indeed
        take the non-refraction corrected zenith angle.
        """
        # --- CONSTANTS ---
        USE_DELTA_KT_PRIME = True
        CALC_GT_90 = False  # don't calc AOI > 90 degrees
        MAX_ITERATIONS = 30  # default

        # Create Inputs DataFrame
        median_rotations = merge_by_dimension(
            data_series=[
                surface_tilt,
                surface_azimuth,
                aoi,
            ],
            merge_how=MergeHow.LEFT,
            indeces=indeces,
        )
        median_rotations = (
            median_rotations.groupby(["time", "met_name"]).median().reset_index()
        )

        met_data = merge_by_dimension(
            data_series=[poa, solar_zenith, solar_azimuth, temp_dew],
            merge_how=MergeHow.LEFT,
            indeces=indeces,
        )

        inputs = pd.merge(
            left=met_data,
            right=median_rotations,
            on=["time", "met_name"],
            how="inner",
        )

        match model:
            case ModelRetroTransposition.GTI_DIRINT:
                inputs = inputs.set_index("time")
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")

                        components = pvlib.irradiance.gti_dirint(
                            poa_global=inputs["poa"],
                            aoi=inputs["aoi"],
                            solar_zenith=inputs["zenith"],  # not corrected
                            solar_azimuth=inputs["azimuth"],
                            times=inputs.index,
                            surface_tilt=inputs["surface_tilt"],
                            surface_azimuth=inputs["surface_azimuth"],
                            pressure=site_pressure,
                            use_delta_kt_prime=USE_DELTA_KT_PRIME,
                            temp_dew=inputs["tdew"],
                            albedo=ALBEDO,
                            model="perez",
                            model_perez="allsitescomposite1990",
                            calculate_gt_90=CALC_GT_90,
                            max_iterations=MAX_ITERATIONS,
                        )
                except UnboundLocalError as e:
                    raise KnownException(
                        error_type=KnownExceptionType.GTI_DIRINT_NON_CONVERGENCE,
                        message=f"GTI Dirint Non Convergence: {e}",
                    )
                except ValueError as e:
                    raise KnownException(
                        error_type=KnownExceptionType.GTI_DIRINT_NON_CONVERGENCE,
                        message=f"GTI Dirint No AOI data < 90.0 degrees: {e}",
                    )
                except Exception as e:
                    raise ValueError(f"Unexpected error in GTI Dirint: {e}")

            case _:
                raise ValueError(f"Unknown model: {model}.  Must be GTI_DIRINT")

        # Only positional indices allowed
        inputs = inputs.reset_index()
        components = components.reset_index()

        ghi = components.loc[:, "ghi"].rename("ghi_retro")
        dhi = components.loc[:, "dhi"].rename("dhi_retro")
        dni = components.loc[:, "dni"].rename("dni_retro")

        self.ghi_retro = MetTimeSeries(ghi)
        self.dhi_retro = MetTimeSeries(dhi)
        self.dni_retro = MetTimeSeries(dni)
