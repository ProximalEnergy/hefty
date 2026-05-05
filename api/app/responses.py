from typing import Any

import pydantic_core
from fastapi.responses import JSONResponse


class NaNSafeJSONResponse(JSONResponse):
    """JSONResponse that serializes NaN/Inf floats as null via pydantic-core."""

    def render(  # no-star-syntax
        self,
        content: Any,
    ) -> bytes:
        """Serialize content to JSON bytes with NaN/Inf coerced to null.

        Args:
            content: The response content to serialize.

        Returns:
            JSON-encoded bytes.
        """
        return pydantic_core.to_json(content, inf_nan_mode="null")
