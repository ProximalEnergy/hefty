from dataclasses import dataclass

from interfaces import Indeces, ModuleEquipmentSeries, StringMetTimeSeries, SystemSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p3_epoai.s01_direct_shade import EPOAIafterFrontShade


@dataclass(init=False, slots=True)
class EPOAIfterElectricalEffect:
    """EPOAIfterElectricalEffect."""

    beam: StringMetTimeSeries
    circumsolar: StringMetTimeSeries
    horizon: StringMetTimeSeries
    isotropic: StringMetTimeSeries
    ground_diffuse: StringMetTimeSeries
    rear: StringMetTimeSeries

    def __init__(
        self,
        indeces: Indeces,
        epoai_after_front_shade: EPOAIafterFrontShade,
        module_id_by_string: SystemSeries,
        module_technology: ModuleEquipmentSeries,
        module_is_half_cut: ModuleEquipmentSeries,
    ):
        """Calculate the electrical effect of shading on PV modules.

        Parameters:
        epoai_direct_shade (pd.DataFrame): DataFrame containing direct shading data.
        modules (pd.DataFrame): DataFrame containing module data.

        Returns:
        pd.DataFrame: DataFrame containing electrical effect data.
        """
        # --- HARDCODED ---
        # Shade threshold should be about one cell length before beam
        # contribution to epoai is neglected.  This matches PVsyst v8+.
        # This is a rough calculation and doesn't account for
        # the encapsulant or frame.
        SHADE_THRESHOLD = 1 / 12
        ELECTRICAL_EFFECT_FULL_CELL = 0.96
        ELECTRICAL_EFFECT_HALF_CELL = 0.50

        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                epoai_after_front_shade.beam,
                epoai_after_front_shade.direct_shade_fraction,
                module_id_by_string,
                module_technology,
                module_is_half_cut,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- EXECUTE ---
        # Normal crystalline silicon modules
        inputs.loc[
            (inputs["technology"] == "c-Si")
            & (~inputs["half_cut"])
            & (inputs["direct_shade_fraction"] > SHADE_THRESHOLD),
            "beam",
        ] = inputs["beam"] * (1 - ELECTRICAL_EFFECT_FULL_CELL)

        # Half-cut crystalline silicon modules
        inputs.loc[
            (inputs["technology"] == "c-Si")
            & (inputs["half_cut"])
            & (inputs["direct_shade_fraction"] > SHADE_THRESHOLD),
            "beam",
        ] = inputs["beam"] * (1 - ELECTRICAL_EFFECT_HALF_CELL)

        # --- Assignments ---
        # Pass throughs
        self.isotropic = epoai_after_front_shade.isotropic
        self.circumsolar = epoai_after_front_shade.circumsolar
        self.horizon = epoai_after_front_shade.horizon
        self.ground_diffuse = epoai_after_front_shade.ground_diffuse
        self.rear = epoai_after_front_shade.rear

        # Calculations
        self.beam = StringMetTimeSeries((inputs.loc[:, "beam"]).rename("beam"))
