from unittest.mock import AsyncMock, MagicMock

import pytest
from app._crud.operational.manufacturer_model_ids import (
    lookup_ids_by_manufacturer_model_pairs,
)

from core import models


@pytest.mark.asyncio
async def test_lookup_ids_empty_input_skips_query() -> None:
    """Empty manufacturer/model lists return no IDs without querying."""
    db = MagicMock()
    db.execute = AsyncMock()

    result = await lookup_ids_by_manufacturer_model_pairs(
        db=db,
        manufacturers=[],
        model_names=[],
        manufacturers_list_name="manufacturers",
        model_names_list_name="models",
        id_column=models.Inverter.inverter_id,
        manufacturer_column=models.Inverter.manufacturer,
        model_column=models.Inverter.model,
    )

    assert result == []
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_lookup_ids_mismatched_lengths_raises() -> None:
    """Mismatched manufacturer/model lists raise a clear error."""
    db = MagicMock()

    with pytest.raises(ValueError, match="must have the same length"):
        await lookup_ids_by_manufacturer_model_pairs(
            db=db,
            manufacturers=["Acme"],
            model_names=[],
            manufacturers_list_name="inverter_manufacturers",
            model_names_list_name="inverter_models",
            id_column=models.Inverter.inverter_id,
            manufacturer_column=models.Inverter.manufacturer,
            model_column=models.Inverter.model,
        )
