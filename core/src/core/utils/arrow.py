import io
from typing import TYPE_CHECKING

import polars as pl
import pyarrow as pa

if TYPE_CHECKING:
    from fastapi.responses import Response


def polars_to_arrow_response(
    *,
    df: pl.DataFrame,
    filename: str = "data.arrow",
) -> "Response":
    """
    Convert a Polars DataFrame to an Apache Arrow IPC Response.

    This function creates a FastAPI Response containing the DataFrame
    serialized in Apache Arrow IPC format (Feather v2).

    Args:
        df: The Polars DataFrame to convert
        filename: The filename to use in the Content-Disposition header

    Returns:
        A FastAPI Response with Arrow IPC format content
    """
    # Convert Polars DataFrame to PyArrow Table
    arrow_table = df.to_arrow()

    # Serialize to Arrow IPC format (feather format)
    buffer = io.BytesIO()
    with pa.ipc.new_file(buffer, arrow_table.schema) as writer:
        writer.write_table(arrow_table)

    # Return as response with appropriate media type
    buffer.seek(0)

    # # Import Response here to avoid circular imports
    # from fastapi.responses import Response

    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.apache.arrow.file",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Total-Records": str(len(df)),
        },
    )
