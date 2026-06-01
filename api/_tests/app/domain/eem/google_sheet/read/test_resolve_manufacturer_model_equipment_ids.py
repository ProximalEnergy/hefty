from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest
from app.domain.eem.google_sheet.read._resolve_manufacturer_model_equipment_ids import (
    resolve_manufacturer_model_equipment_ids,
)
from fastapi.exceptions import HTTPException


@pytest.mark.asyncio
async def test_resolve_merges_ids_and_drops_sheet_columns() -> None:
    """Resolved IDs are merged and temporary sheet columns are removed."""
    system = pd.DataFrame(
        {
            "Module Manufacturer": ["Acme", "Acme", "Other"],
            "Module Model": ["X1", "X1", "Z9"],
            "Module Bin Class": ["A", "A", "B"],
            "keep_me": [1, 2, 3],
        },
    )
    lookup_ids = AsyncMock(return_value=[10, 20])

    result = await resolve_manufacturer_model_equipment_ids(
        db=MagicMock(),
        system=system,
        manufacturer_column="Module Manufacturer",
        model_column="Module Model",
        gsheet_id_column="gsheet_module_id",
        output_id_column="pv_module_id",
        entity_plural="modules",
        lookup_ids=lookup_ids,
        lookup_manufacturers_argument="pv_module_manufacturers",
        lookup_models_argument="pv_module_models",
        extra_drop_columns=["Module Bin Class"],
    )

    assert list(result["pv_module_id"]) == [10, 10, 20]
    assert "Module Manufacturer" not in result.columns
    assert "Module Model" not in result.columns
    assert "Module Bin Class" not in result.columns
    assert "keep_me" in result.columns
    lookup_ids.assert_awaited_once()
    call_args = lookup_ids.await_args
    assert call_args is not None
    assert call_args.kwargs["pv_module_manufacturers"] == ["Acme", "Other"]
    assert call_args.kwargs["pv_module_models"] == ["X1", "Z9"]


@pytest.mark.asyncio
async def test_resolve_missing_id_raises_with_entity_plural() -> None:
    """Missing equipment IDs raise HTTP 400 naming the configured entity type."""
    system = pd.DataFrame(
        {
            "PCS Manufacturer": ["MissingCo"],
            "PCS Model": ["NoModel"],
        },
    )
    lookup_ids = AsyncMock(return_value=[None])

    with pytest.raises(HTTPException) as exc_info:
        await resolve_manufacturer_model_equipment_ids(
            db=MagicMock(),
            system=system,
            manufacturer_column="PCS Manufacturer",
            model_column="PCS Model",
            gsheet_id_column="gsheet_inverter_id",
            output_id_column="inverter_equipment_id",
            entity_plural="inverters",
            lookup_ids=lookup_ids,
            lookup_manufacturers_argument="inverter_manufacturers",
            lookup_models_argument="inverter_models",
        )

    assert exc_info.value.status_code == 400
    assert "inverters" in exc_info.value.detail
    assert "MissingCo NoModel" in exc_info.value.detail
