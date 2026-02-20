from interfaces import Indeces, ModuleEquipmentSeries, SystemSeries
from p01_get_data.source_proximal.s04_get_system_data import System
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension


def calc_pitch(
    system: System,
    indeces: Indeces,
    module_ids_by_string: SystemSeries,
    racking_controls_gcr: SystemSeries,
    module_length: ModuleEquipmentSeries,
):
    # --- Merge ---
    """Run calc_pitch."""
    inputs = merge_by_dimension(
        data_series=[
            module_ids_by_string,
            racking_controls_gcr,
            module_length,
        ],
        indeces=indeces,
        merge_how=MergeHow.LEFT,
    )
    # --- Pitch Calculation ---
    pitch_series = inputs["length"] / inputs["racking_controls_gcr"]
    pitch_series.name = "pitch"
    pitch = SystemSeries(pitch_series)

    # --- Assignment ---
    system.pitch = pitch
