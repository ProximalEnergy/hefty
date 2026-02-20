from dataclasses import dataclass

import sqlalchemy
from interfaces import Indeces, MetDataObserved, QualityAssurance
from p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from p01_get_data.s00_get_simulation_config import SimulationConfig
from p01_get_data.source_proximal.c01_get_proximal_data import (
    from_proximal_db,
)
from p01_get_data.source_proximal.s03_get_project import Project
from p01_get_data.source_proximal.s04_get_system_data import System
from p01_get_data.source_proximal.s09_get_inverter_data import Inverter
from p01_get_data.source_proximal.s09_get_module_data import Module
from p01_get_data.source_proximal.s09_get_racking_data import Racking

# from _utils import export_class_to_dill, import_class_from_dill


@dataclass(slots=True)
class SimulationInputs:
    """A class for handling simulation inputs, can be extended
    with other builder style methods for different types of inputs.

    Attributes:
        met_data (pd.DataFrame): Weather data for project sites.
        met_locations (pd.DataFrame): Location data for met stations.
        simulation_config (SimulationConfig): Configuration for simulation.
    """

    version: str
    project: Project
    indeces: Indeces
    quality_assurance: QualityAssurance
    met_data: MetDataObserved
    simulation_config: SimulationConfig
    system: System
    modules: Module
    rackings: Racking
    inverters: Inverter
    axis_azimuth: float
    engine: sqlalchemy.engine.Engine
    SIMULATION_TEMPORAL_MODE: SimulationTemporalMode
    ENVIRONMENT: str

    # --- Imported Builder Methods ---
    from_proximal_db = classmethod(from_proximal_db)
