from __future__ import annotations

from collections.abc import Mapping
from typing import Generic, Literal, TypeVar, overload

import pandas as pd
import polars as pl
from sqlalchemy import Select, TextClause
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.orm import Session

T = TypeVar("T")
S = TypeVar(
    "S",
    bound=Literal[True] | Literal[False],
    default=Literal[False],
)
_SQL_TO_MODEL_COL_MAP: Mapping[str, str]

from core.enumerations import OutputType as OutputType

class DbQuery(Generic[T, S]):
    query: TextClause | Select
    sql_string: str
    is_scalar: S
    use_scalars: bool

    @overload
    def __init__(
        self: DbQuery[RowMapping, Literal[True]],
        *,
        query: TextClause,
        is_scalar: Literal[True],
    ) -> None: ...
    @overload
    def __init__(
        self: DbQuery[RowMapping, Literal[False]],
        *,
        query: TextClause,
        is_scalar: Literal[False] = False,
        use_scalars: bool = True,
    ) -> None: ...
    @overload
    def __init__(
        self: DbQuery[T, Literal[True]],
        *,
        query: Select,
        is_scalar: Literal[True],
    ) -> None: ...
    @overload
    def __init__(
        self: DbQuery[T, Literal[False]],
        *,
        query: Select,
        is_scalar: Literal[False] = False,
        use_scalars: bool = True,
    ) -> None: ...
    @overload
    def _read_data(
        self,
        *,
        conn: Connection,
        output_type: Literal[OutputType.POLARS],
    ) -> pl.DataFrame: ...
    @overload
    def _read_data(
        self,
        *,
        conn: Connection,
        output_type: Literal[OutputType.PANDAS],
    ) -> pd.DataFrame: ...
    @overload
    def _read_data(
        self: DbQuery[T, Literal[False]],
        *,
        session: Session,
        output_type: Literal[OutputType.SQLALCHEMY],
    ) -> list[T]: ...
    @overload
    def _read_data(
        self: DbQuery[T, Literal[True]],
        *,
        session: Session,
        output_type: Literal[OutputType.SQLALCHEMY],
    ) -> T | None: ...
    @overload
    def _read_data(
        self: DbQuery[T, Literal[False]],
        *,
        conn: Connection | None = None,
        session: Session | None = None,
        output_type: OutputType,
    ) -> pd.DataFrame | pl.DataFrame | list[T]: ...
    @overload
    def _read_data(
        self: DbQuery[T, Literal[True]],
        *,
        conn: Connection | None = None,
        session: Session | None = None,
        output_type: OutputType,
    ) -> pd.DataFrame | pl.DataFrame | T | None: ...
    @overload
    def get(
        self,
        *,
        schema: str | None = "operational",
        output_type: Literal[OutputType.POLARS] = OutputType.POLARS,
    ) -> pl.DataFrame: ...
    @overload
    def get(
        self,
        *,
        schema: str | None = "operational",
        output_type: Literal[OutputType.PANDAS],
    ) -> pd.DataFrame: ...
    @overload
    def get(
        self: DbQuery[T, Literal[False]],
        *,
        schema: str | None = "operational",
        output_type: Literal[OutputType.SQLALCHEMY],
    ) -> list[T]: ...
    @overload
    def get(
        self: DbQuery[T, Literal[True]],
        *,
        schema: str | None = "operational",
        output_type: Literal[OutputType.SQLALCHEMY],
    ) -> T | None: ...
    @overload
    def get(
        self: DbQuery[T, Literal[False]],
        *,
        schema: str | None = "operational",
        output_type: OutputType = OutputType.POLARS,
    ) -> pd.DataFrame | pl.DataFrame | list[T]: ...
    @overload
    def get(
        self: DbQuery[T, Literal[True]],
        *,
        schema: str | None = "operational",
        output_type: OutputType = OutputType.POLARS,
    ) -> pd.DataFrame | pl.DataFrame | T | None: ...
    @overload
    async def get_async(
        self,
        *,
        schema: str | None = "operational",
        output_type: Literal[OutputType.POLARS] = OutputType.POLARS,
    ) -> pl.DataFrame: ...
    @overload
    async def get_async(
        self,
        *,
        schema: str | None = "operational",
        output_type: Literal[OutputType.PANDAS],
    ) -> pd.DataFrame: ...
    @overload
    async def get_async(
        self: DbQuery[T, Literal[False]],
        *,
        schema: str | None = "operational",
        output_type: Literal[OutputType.SQLALCHEMY],
    ) -> list[T]: ...
    @overload
    async def get_async(
        self: DbQuery[T, Literal[True]],
        *,
        schema: str | None = "operational",
        output_type: Literal[OutputType.SQLALCHEMY],
    ) -> T | None: ...
    @overload
    async def get_async(
        self: DbQuery[T, Literal[False]],
        *,
        schema: str | None = "operational",
        output_type: OutputType = OutputType.POLARS,
    ) -> pd.DataFrame | pl.DataFrame | list[T]: ...
    @overload
    async def get_async(
        self: DbQuery[T, Literal[True]],
        *,
        schema: str | None = "operational",
        output_type: OutputType = OutputType.POLARS,
    ) -> pd.DataFrame | pl.DataFrame | T | None: ...
    @overload
    def _apply_mapping(self, *, df: pd.DataFrame) -> pd.DataFrame: ...
    @overload
    def _apply_mapping(self, *, df: pl.DataFrame) -> pl.DataFrame: ...
    def _normalize_pandas_dtypes(
        self,
        *,
        df: pd.DataFrame,
        strings_as_object: bool = True,
    ) -> pd.DataFrame: ...

def postprocess_pandas_df(
    *,
    df: pd.DataFrame,
    index: str | None = None,
    as_datetime: bool = False,
    tz: str | None = None,
) -> pd.DataFrame: ...
