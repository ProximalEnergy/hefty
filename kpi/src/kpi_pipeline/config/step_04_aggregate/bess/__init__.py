from kpi_pipeline.config.step_04_aggregate.bess.availability import (
    AggregateBESSAvailability,
)
from kpi_pipeline.config.step_04_aggregate.bess.energy import AggregateBESSEnergy
from kpi_pipeline.config.step_04_aggregate.bess.operational import (
    AggregateBESSOperational,
)
from kpi_pipeline.config.step_04_aggregate.bess.state import AggregateBESSState
from kpi_pipeline.config.step_04_aggregate.bess.temperature import (
    AggregateBESSTemperature,
)
from kpi_pipeline.config.step_04_aggregate.bess.voltage import AggregateBESSVoltage


class AggregateBESS(
    AggregateBESSAvailability,
    AggregateBESSOperational,
    AggregateBESSEnergy,
    AggregateBESSState,
    AggregateBESSTemperature,
    AggregateBESSVoltage,
):
    pass
