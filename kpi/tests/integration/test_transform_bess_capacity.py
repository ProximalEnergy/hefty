"""Integration checks for BESS clean project capacity (energy and power)."""

import numpy as np
import pytest
import xarray as xr
from kpi.base.exception import ValidationError
from kpi.base.protocol import CalcProtocol
from kpi.workflow.download.project_attribute.workflow import (
    DownloadProjectAttribute as Download,
)
from kpi.workflow.transform.bess.clean.project_attribute import (
    TransformBessCleanProjectAttribute as Project,
)

_CASES: tuple[tuple[str, CalcProtocol], ...] = (
    (
        Download.project_energy_capacity_raw_kwh.name,
        Project.project_energy_capacity_kwh.value,
    ),
    (
        Download.project_power_capacity_raw_kw.name,
        Project.project_power_capacity_kw.value,
    ),
)


def _run_transform(*, raw: str, clean: CalcProtocol, raw_value: float) -> xr.DataArray:
    """Run the clean transform for a single project capacity field."""
    ds = xr.Dataset({raw: xr.DataArray(raw_value)})
    return clean.run(ds)


@pytest.mark.parametrize(("raw", "clean"), _CASES)
def test_project_capacity_unchanged_when_raw_positive(
    raw: str,
    clean: CalcProtocol,
) -> None:
    """Positive raw capacity is copied unchanged to the clean field."""
    value = 12_500.0
    out = _run_transform(raw=raw, clean=clean, raw_value=value)
    assert float(out.values.item()) == value


@pytest.mark.parametrize(("raw", "clean"), _CASES)
@pytest.mark.parametrize("raw_value", [0.0, -1.0, np.nan])
def test_project_capacity_raises_when_raw_not_positive(
    raw: str,
    clean: CalcProtocol,
    raw_value: float,
) -> None:
    """Non-positive raw capacity raises ``ValidationError``."""
    with pytest.raises(ValidationError):
        _run_transform(raw=raw, clean=clean, raw_value=raw_value)
