import xarray as xr

from kpi_pipeline.base.protocols import ActionProtocol
from kpi_pipeline.services.action.action import (
    EmptyAction,
    TransformAction,
)
from kpi_pipeline.services.action.transform import TransformList


def action_from_list(steps: list[ActionProtocol]) -> ActionProtocol:
    if len(steps) == 0:
        return EmptyAction()
    elif len(steps) == 1:
        return steps[0]
    else:
        return TransformAction(
            transform=TransformList(steps=steps[:-1]),
            action=steps[-1],
        )


def sort_vars(dataset: xr.Dataset) -> xr.Dataset:
    variable_names = list(dataset.data_vars.keys())
    sorted_variable_names = sorted(variable_names)
    return dataset[sorted_variable_names]
