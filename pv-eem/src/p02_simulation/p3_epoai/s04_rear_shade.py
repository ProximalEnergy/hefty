from dataclasses import dataclass

from interfaces import (
    Indeces,
    ModuleEquipmentSeries,
    RackingEquipmentSeries,
    StringMetTimeSeries,
    SystemSeries,
)
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p3_epoai.s03_diffuse_shade import EPOAIafterDiffuseShade


@dataclass(init=False, slots=True)
class EPOAIafterRearShade:
    """EPOAIafterRearShade."""

    beam: StringMetTimeSeries
    circumsolar: StringMetTimeSeries
    horizon: StringMetTimeSeries
    isotropic: StringMetTimeSeries
    ground_diffuse: StringMetTimeSeries
    rear: StringMetTimeSeries

    def __init__(
        self,
        epoai_after_diffuse_shade: EPOAIafterDiffuseShade,
        indeces: Indeces,
        racking_id_by_string: SystemSeries,
        module_id_by_string: SystemSeries,
        structure_shading_factor: RackingEquipmentSeries,
        rear_mismatch_factor: RackingEquipmentSeries,
        bifaciality_factor: ModuleEquipmentSeries,
    ):
        # --- Merge ---
        inputs = merge_by_dimension(
            data_series=[
                epoai_after_diffuse_shade.rear,
                # racking fields
                racking_id_by_string,
                structure_shading_factor,
                rear_mismatch_factor,
                # module fields
                module_id_by_string,
                bifaciality_factor,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- Assignments ---
        # pass throughs
        self.beam = epoai_after_diffuse_shade.beam
        self.circumsolar = epoai_after_diffuse_shade.circumsolar
        self.horizon = epoai_after_diffuse_shade.horizon
        self.isotropic = epoai_after_diffuse_shade.isotropic
        self.ground_diffuse = epoai_after_diffuse_shade.ground_diffuse

        # calculations
        structure_shading_loss = 1 - inputs["structure_shading_factor"]
        rear_shading_loss = 1 - inputs["rear_mismatch_factor"]
        self.rear = StringMetTimeSeries(
            epoai_after_diffuse_shade.rear
            * structure_shading_loss
            * rear_shading_loss
            * inputs["bifaciality_factor"]
        )
