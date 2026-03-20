from kpi_pipeline.config.step_04_aggregate import Aggregate
from kpi_pipeline.config.step_04_aggregate.exceptions.bexar import AggregateBexar

aggregate_per_project = {
    "base": Aggregate,
    "bexar": AggregateBexar,
}
