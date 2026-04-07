"""Integration checks for BESS clean project capacity (energy and power)."""

import pytest
import xarray as xr
from kpi.base.exception import ValidationError
from kpi.workflow.download.project_attribute.workflow import (
    DownloadProjectAttribute as Download,
)
from kpi.workflow.transform.bess.clean.project_attribute import (
    TransformBessCleanProjectAttribute,
)

T = TransformBessCleanProjectAttribute

_CASES: tuple[tuple[str, str], ...] = (
    (T.project_energy_capacity_kwh.name, Download.project_energy_capacity_raw_kwh.name),
    (T.project_power_capacity_kw.name, Download.project_power_capacity_raw_kw.name),
)


def _run_transform(*, clean: str, raw: str, raw_value: float) -> xr.Dataset:
    """Run the clean transform for a single project capacity field."""
    ds = xr.Dataset({raw: xr.DataArray(raw_value)})
    schema = T()
    required = schema.compile({clean})
    assert required == {raw}
    return schema.run(ds)


@pytest.mark.parametrize(("clean", "raw"), _CASES)
def test_project_capacity_unchanged_when_raw_positive(
    clean: str,
    raw: str,
) -> None:
    """Positive raw capacity is copied unchanged to the clean field."""
    value = 12_500.0
    out = _run_transform(clean=clean, raw=raw, raw_value=value)
    assert clean in out.data_vars
    assert raw not in out.data_vars
    assert float(out[clean].values) == value


@pytest.mark.parametrize(("clean", "raw"), _CASES)
@pytest.mark.parametrize("raw_value", [0.0, -1.0])
def test_project_capacity_raises_when_raw_not_positive(
    clean: str,
    raw: str,
    raw_value: float,
) -> None:
    """Non-positive raw capacity raises ``ValidationError``."""
    with pytest.raises(ValidationError):
        _run_transform(clean=clean, raw=raw, raw_value=raw_value)
