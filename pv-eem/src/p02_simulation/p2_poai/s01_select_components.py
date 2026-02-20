from dataclasses import dataclass

from interfaces import (
    Indeces,
    MetTimeSeries,
    QualityAssurance,
)
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p2_poai.s00_retro_transposition import HorizontalIrradianceRetro


@dataclass(init=False, slots=True)
class HorizontalIrradiance:
    """HorizontalIrradiance."""

    ghi: MetTimeSeries
    dni: MetTimeSeries
    dhi: MetTimeSeries
    tier: MetTimeSeries
    tier_codes: MetTimeSeries

    def __init__(
        self,
        indeces: Indeces,
        quality_assurance: QualityAssurance,
        horizontal_irradiance_retro: HorizontalIrradianceRetro,
        ghi: MetTimeSeries,
        dni: MetTimeSeries,
        dhi: MetTimeSeries,
        use_poa_only: bool,
    ):
        """Select the components for the POAI calculation
        Tier 1 simulations will use the retro-transposed components
        Tier 3 simulations will use the measured horizontal components
        """
        # --- Constants ---
        TIER_1_CUTOFF = 1.15

        df = merge_by_dimension(
            data_series=[
                quality_assurance.tier,
                quality_assurance.tier_codes,
                horizontal_irradiance_retro.ghi_retro,
                horizontal_irradiance_retro.dni_retro,
                horizontal_irradiance_retro.dhi_retro,
                ghi,
                dni,
                dhi,
            ],
            merge_how=MergeHow.LEFT,
            indeces=indeces,
        )
        if use_poa_only:
            df.loc[:, "tier"] = 3
            df.loc[:, "tier_codes"] = "poa_from_decomp"

            self.ghi = MetTimeSeries(df.loc[:, "ghi_retro"].rename("ghi"))
            self.dni = MetTimeSeries(df.loc[:, "dni_retro"].rename("dni"))
            self.dhi = MetTimeSeries(df.loc[:, "dhi_retro"].rename("dhi"))
            self.tier = MetTimeSeries(df.loc[:, "tier"])
            self.tier_codes = MetTimeSeries(df.loc[:, "tier_codes"])

        else:
            # --- Determine which components to use ---
            df["ghi_ratio"] = df["ghi"] / df["ghi_retro"]
            mask_1 = (df["ghi_ratio"] > TIER_1_CUTOFF) | (df["ghi_retro"].isna())
            df.loc[mask_1, "tier"] = 3
            df.loc[mask_1, "tier_codes"] = "poa_from_decomp"

            # use retro-transposed components for tier 1
            mask_2 = (df["ghi_ratio"] < TIER_1_CUTOFF) | (df["ghi_retro"].notna())
            for col in ["ghi", "dni", "dhi"]:
                df.loc[~mask_2, col] = df[f"{col}_retro"]

            # --- Assignments ---
            self.ghi = MetTimeSeries(df.loc[:, "ghi"])
            self.dni = MetTimeSeries(df.loc[:, "dni"])
            self.dhi = MetTimeSeries(df.loc[:, "dhi"])

            self.tier = MetTimeSeries(df.loc[:, "tier"])
            self.tier_codes = MetTimeSeries(df.loc[:, "tier_codes"])
