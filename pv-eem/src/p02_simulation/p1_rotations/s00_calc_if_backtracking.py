from interfaces import Indeces, ModuleEquipmentSeries, SystemSeries
from p01_get_data.source_proximal.s04_get_system_data import (
    RackingControlsAlgorithm,
    System,
)
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension


def calc_if_backtracking(
    *,
    indeces: Indeces,
    system: System,
    module_ids_by_string: SystemSeries,
    module_technology: ModuleEquipmentSeries,
) -> None:
    """Calculate if a system is backtracking from module cell technology.

    Returns:
        pd.DataFrame: The system data with a 'backtrack' column indicating if the system
        is backtracking.
    """
    # --- MERGE IN MODULE DATA---
    df = merge_by_dimension(
        data_series=[
            module_ids_by_string,
            module_technology,
        ],
        merge_how=MergeHow.LEFT,
        indeces=indeces,
    )

    # --- Compute which algorithm to use ---
    df["racking_controls_algorithm"] = RackingControlsAlgorithm.BACK_TRACKING_2D.value
    df.loc[df["technology"] == "CdTe", "racking_controls_algorithm"] = (
        RackingControlsAlgorithm.TRUE_TRACKING_2D.value
    )

    # --- Categorical ---
    df["racking_controls_algorithm"] = df["racking_controls_algorithm"].astype(
        "category"
    )

    # --- Assignment ---
    system.racking_controls_algorithm = SystemSeries(
        df.loc[:, "racking_controls_algorithm"]
    )
