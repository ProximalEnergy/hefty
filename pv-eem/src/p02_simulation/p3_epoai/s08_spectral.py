from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
import pvlib
from interfaces import (
    Indeces,
    MetTimeSeries,
    ModuleEquipmentSeries,
    StringMetTimeSeries,
    SystemSeries,
    TimeSeries,
)
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.data_factorizer import factorize
from p02_simulation.p3_epoai.s07_diffuse_iam import EPOAIafterDiffuseIAM


class ModelSpectral(StrEnum):
    """ModelSpectral."""

    FIRST_SOLAR = "FirstSolar"


@dataclass(slots=True, init=False)
class EPOAIafterSpectral:
    """EPOAIafterSpectral."""

    beam: StringMetTimeSeries
    horizon: StringMetTimeSeries
    isotropic: StringMetTimeSeries
    circumsolar: StringMetTimeSeries
    ground_diffuse: StringMetTimeSeries
    rear: StringMetTimeSeries

    def __init__(
        self,
        *,
        model_spectral: ModelSpectral,
        indeces: Indeces,
        epoai_diffuse_iam: EPOAIafterDiffuseIAM,
        module_id_by_string: SystemSeries,
        module_technology: ModuleEquipmentSeries,
        air_mass_absolute: TimeSeries,
        precipitable_water: MetTimeSeries,
    ):
        """Calculate the effective plane of array irradiance (EPOAI)
        after applying spectral correction factors.

        Args:
            model_spectral: which spectral model to use
            indeces: time and location indices
            epoai_diffuse_iam: effective plane of array irradiance after diffuse IAM
            module_id_by_string: module ID for each string
            module_technology: module technology type
            air_mass_absolute: absolute air mass values
            precipitable_water: precipitable water values

        Returns:
            EPOAI with spectral correction applied:
                EPOAI_spectral = EPOAI_diffuse_iam * spectral_factor
        """
        # --- CONSTANTS ---
        MIN_PRECIPITABLE_WATER = 0.1  # Default
        MAX_PRECIPITABLE_WATER = 8.0  # Default
        MIN_AIRMASS_ABSOLUTE = 0.58  # Default
        MAX_AIRMASS_ABSOLUTE = 10.0  # Default

        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                epoai_diffuse_iam.beam,  # just to get StringMetTimeIndex
                module_id_by_string,
                module_technology,
                air_mass_absolute,
                precipitable_water,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- FACTORIZE ---
        inputs = factorize(
            dataframe=inputs,
            columns=["technology", "air_mass_absolute", "precipitable_water"],
            rounding_precision=2,
        )

        unique_by_group = inputs.groupby("_unique_id").first()

        # --- FUNCTION ---
        match model_spectral:
            case ModelSpectral.FIRST_SOLAR:
                # Initialize all spectral factors as 1.0
                spectral = pd.Series(1.0, index=unique_by_group.index)

                # Calculate the spectral mismatch only on CdTe modules
                cdte_mask = unique_by_group["technology"] == "CdTe"
                if cdte_mask.any():
                    spectral[cdte_mask] = pvlib.spectrum.spectral_factor_firstsolar(
                        precipitable_water=unique_by_group.loc[
                            cdte_mask, "precipitable_water"
                        ],
                        airmass_absolute=unique_by_group.loc[
                            cdte_mask, "air_mass_absolute"
                        ],
                        module_type="cdte",
                        min_precipitable_water=MIN_PRECIPITABLE_WATER,
                        max_precipitable_water=MAX_PRECIPITABLE_WATER,
                        min_airmass_absolute=MIN_AIRMASS_ABSOLUTE,
                        max_airmass_absolute=MAX_AIRMASS_ABSOLUTE,
                    )
            case _:
                raise ValueError(f"Unknown spectral model: {model_spectral}")

        # Only allow dataframes with positional indices
        spectral = spectral.rename("spectral")

        # --- REJOIN ---
        outputs = pd.merge(
            left=inputs,
            right=spectral,
            on=["_unique_id"],
            how="left",
        )

        # --- APPLY SPECTRAL CORRECTION ---
        # Apply spectral correction to all plane of array components
        self.beam = StringMetTimeSeries(
            (epoai_diffuse_iam.beam * outputs["spectral"]).rename("beam")
        )
        self.circumsolar = StringMetTimeSeries(
            (epoai_diffuse_iam.circumsolar * outputs["spectral"]).rename("circumsolar")
        )
        self.isotropic = StringMetTimeSeries(
            (epoai_diffuse_iam.isotropic * outputs["spectral"]).rename("isotropic")
        )
        self.horizon = StringMetTimeSeries(
            (epoai_diffuse_iam.horizon * outputs["spectral"]).rename("horizon")
        )
        self.ground_diffuse = StringMetTimeSeries(
            (epoai_diffuse_iam.ground_diffuse * outputs["spectral"]).rename(
                "ground_diffuse"
            )
        )
        self.rear = StringMetTimeSeries(
            (epoai_diffuse_iam.rear * outputs["spectral"]).rename("rear")
        )
