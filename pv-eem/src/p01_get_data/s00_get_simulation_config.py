import logging
from dataclasses import dataclass, field
from enum import StrEnum

from p02_simulation.p0_meteorological.s02_solar_position import (
    ModelSolarPositionAlgorithm,
)
from p02_simulation.p0_meteorological.s03_air_mass import (
    ModelAirMassAbsolute,
    ModelAirMassRelative,
)
from p02_simulation.p0_meteorological.s04_tdew import ModelTDew
from p02_simulation.p0_meteorological.s06_dni_extra import ModelExtraTerrestrialDNI
from p02_simulation.p0_meteorological.s07_dni import ModelDecomposition
from p02_simulation.p2_poai.s00_retro_transposition import ModelRetroTransposition
from p02_simulation.p2_poai.s02_sky_diffuse import ModelTransposition
from p02_simulation.p2_poai.s05_rear_poa import ModelRearPOA
from p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
from p02_simulation.p3_epoai.s05_soiling import ModelSoiling
from p02_simulation.p3_epoai.s06_direct_iam import ModelIncidenceAngleModifier
from p02_simulation.p3_epoai.s08_spectral import ModelSpectral
from p02_simulation.p4_dc_iv.s01_cell_temp import ModelThermal
from p02_simulation.p4_dc_iv.s02_single_diode_params import ModelSingleDiode
from p02_simulation.p4_dc_iv.s04_iv_2_warranted_degradation import ModelDegradation
from p02_simulation.p4_dc_iv.s06_iv_4_dc_wiring_to_combiner import (
    ModelDCWiringToCombiner,
)
from p02_simulation.p5_inverter.s00_dc_wiring_to_inverter import ModelDCWiringToInverter
from p02_simulation.p5_inverter.s02_calc_efficiency import ModelInverterEfficiency


@dataclass(slots=True)
class SimulationConfig:
    """* spa:  NREL2008 is the best model available with an uncertainty
        of 0.0003 degrees.
    * decomponsition:  DIRINT is best most practical model since DIRINDEX
        requires aerosol data for hourly data, but ERBS_DRIESSE has a better
        MBE for sub-hourly data according to ineichen 2008.
    * transposition:  Perez is the most popular model.
    * circumsolar: Separate is the most popular becuase it is used
        in pvsyst, but diffuse is safer given retrotransposition is diffuse.
    """

    # --- Meteorological ---
    # # in minutes positive from timestamp beginning
    sun_position_offset: float = field(default=0.0)
    use_poa_only: bool = field(default=False)
    use_median_irr_sensor: bool = field(default=False)
    spa: ModelSolarPositionAlgorithm = field(
        default=ModelSolarPositionAlgorithm.NREL2008
    )
    airmass_relative: ModelAirMassRelative = field(
        default=ModelAirMassRelative.KASTEN_YOUNG_1989
    )
    airmass_absolute: ModelAirMassAbsolute = field(
        default=ModelAirMassAbsolute.GUEYMARD_1993
    )
    dewpoint_temperature: ModelTDew = field(default=ModelTDew.MAGNUS_TETENS)
    extra_terrestrial_dni: ModelExtraTerrestrialDNI = field(
        default=ModelExtraTerrestrialDNI.SPENCER
    )
    decomposition: ModelDecomposition = field(default=ModelDecomposition.ERBS_DRIESSE)
    #
    # --- Plane Of Array Irradiance (POAI) ---
    #
    retro_transposition: ModelRetroTransposition = field(
        default=ModelRetroTransposition.GTI_DIRINT
    )
    transposition: ModelTransposition = field(default=ModelTransposition.PEREZ_DRIESSE)
    rear_poa: ModelRearPOA = field(default=ModelRearPOA.SOLAR_FACTORS)
    #
    # --- Effective Plane Of Array Irradiance (EPOAI) ---
    #
    circumsolar: ModelCircumsolar = field(default=ModelCircumsolar.DIFFUSE)
    soiling: ModelSoiling = field(default=ModelSoiling.NONE)
    iam: ModelIncidenceAngleModifier = field(
        default=ModelIncidenceAngleModifier.PHYSICAL
    )
    spectral: ModelSpectral = field(default=ModelSpectral.FIRST_SOLAR)
    #
    #  --- DC Power ---
    # Thermal
    thermal: ModelThermal = field(default=ModelThermal.PVSYST_CELL)
    thermal_uc: float = field(default=29.0)
    thermal_uv: float = field(default=0.0)
    #
    # Single Diode Model
    #
    single_diode_model: ModelSingleDiode = field(default=ModelSingleDiode.PVSYST)
    #
    # Degradation
    degradation: ModelDegradation = field(default=ModelDegradation.NONE)
    #
    # Wiring
    dc_wiring_to_combiner: ModelDCWiringToCombiner = field(
        default=ModelDCWiringToCombiner.TARGET_STC
    )
    dc_wiring_to_inverter: ModelDCWiringToInverter = field(
        default=ModelDCWiringToInverter.TARGET_STC
    )
    # --- Inverter ---
    #
    inverter_efficiency: ModelInverterEfficiency = field(
        default=ModelInverterEfficiency.SANDIA
    )

    @classmethod
    def initialize_with_overrides(cls, **config_overrides):
        """Run initialize_with_overrides."""
        base_config = SimulationConfig()

        if config_overrides:
            # Convert enum strings to actual enum values if needed
            processed_overrides = {}
            for key, value in config_overrides.items():
                field_type = type(getattr(base_config, key))
                # THIS HAS TO BE STRENUM or it won't work (python enums suck)
                if isinstance(field_type, type) and issubclass(field_type, StrEnum):
                    if isinstance(value, str):
                        processed_overrides[key] = field_type(value)
                    else:
                        processed_overrides[key] = value
                else:
                    processed_overrides[key] = value

            # Create new instance with processed overrides
            logging.info(f"Overriding SimulationConfig with {processed_overrides}")
            return cls(**processed_overrides)

        return base_config
