from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Literal, TypeVar, overload

import pandas as pd
import polars as pl
from sqlalchemy import Select, TextClause
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.orm import Session

T = TypeVar("T")
_SQL_TO_MODEL_COL_MAP: Mapping[str, str]

class OutputType(Enum):
    PANDAS = "pandas"
    POLARS = "polars"
    SQLALCHEMY = "sqlalchemy"

class DbQuery[T]:
    query: TextClause | Select
    sql_string: str

    def __init__(self, *, query: TextClause | Select) -> None: ...
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
        self,
        *,
        session: Session,
        output_type: Literal[OutputType.SQLALCHEMY],
    ) -> Sequence[RowMapping] | Sequence[T]: ...
    @overload
    def _read_data(
        self,
        *,
        conn: Connection | None = None,
        session: Session | None = None,
        output_type: OutputType,
    ) -> pd.DataFrame | pl.DataFrame | Sequence[RowMapping] | Sequence[T]: ...
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
        self,
        *,
        schema: str | None = "operational",
        output_type: Literal[OutputType.SQLALCHEMY],
    ) -> Sequence[RowMapping] | Sequence[T]: ...
    @overload
    def get(
        self,
        *,
        schema: str | None = "operational",
        output_type: OutputType = OutputType.POLARS,
    ) -> pd.DataFrame | pl.DataFrame | Sequence[RowMapping] | Sequence[T]: ...
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
        self,
        *,
        schema: str | None = "operational",
        output_type: Literal[OutputType.SQLALCHEMY],
    ) -> Sequence[RowMapping] | Sequence[T]: ...
    @overload
    async def get_async(
        self,
        *,
        schema: str | None = "operational",
        output_type: OutputType = OutputType.POLARS,
    ) -> pd.DataFrame | pl.DataFrame | Sequence[RowMapping] | Sequence[T]: ...
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
