"""Database query wrapper for efficient Polars and Pandas dataframe operations."""

import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

import pandas as pd
import polars as pl
from pandas.api import types as pdt
from sqlalchemy import Select, TextClause
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm.strategy_options import Load, _LoadElement

from core.database import async_engine, engine
from core.dependencies import with_db, with_db_async

T = TypeVar("T")
_SQL_TO_MODEL_COL_MAP: Mapping[str, str] = {"time_bucket": "time"}
_SQLALCHEMY_ROW_LIMIT = 101
_SQLALCHEMY_ROW_THRESHOLD = 100


def _raise_for_large_sqlalchemy_result(*, count: int) -> None:
    if count >= _SQLALCHEMY_ROW_THRESHOLD:
        raise ValueError(
            "Too many SQLAlchemy rows (>=100). Use pandas or polars instead."
        )


class OutputType(Enum):
    """Enum to select DbQuery fetch output type."""

    PANDAS = "pandas"
    POLARS = "polars"
    SQLALCHEMY = "sqlalchemy"


@dataclass
class DbQuery[T]:
    """
    This class wraps SQL queries (TextClause or Select) and provides
    methods to efficiently load data directly into Polars or Pandas
    dataframes without materializing ORM objects.

    Usage:
        query = DbQuery(query=sql_query)
        df = await query.get_async()

    Recommendations:
        - Use Polars best speed and memory performance on tabular data
        - Use Pandas for compatability with existing code
        - Use SqlAlchemy for selectinload (one to many) operations
    """

    query: TextClause | Select
    is_scalar: bool = False

    def get(
        self,
        *,
        schema: str | None = "operational",
        output_type: OutputType = OutputType.POLARS,
    ) -> (
        pd.DataFrame | pl.DataFrame | list[RowMapping] | list[T] | RowMapping | T | None
    ):
        """
        Execute the query on a sync connection and return data.

        Args:
            schema: Optional schema name for translation map.
            output_type: Output format for the returned data.
        """
        with self._get_sync_context(schema, output_type) as db_obj:
            return self._read_data(
                executor=db_obj,
                output_type=output_type,
            )

    async def get_async(
        self,
        *,
        schema: str | None = "operational",
        output_type: OutputType = OutputType.POLARS,
    ) -> (
        pd.DataFrame | pl.DataFrame | list[RowMapping] | list[T] | RowMapping | T | None
    ):
        """
        Execute the query on an async connection and return data.

        Args:
            schema: Optional schema name for translation map.
            output_type: Output format for the returned data.
        """
        async with self._get_async_context(schema, output_type) as db_obj:
            return await db_obj.run_sync(
                lambda sync_obj: self._read_data(
                    executor=sync_obj,
                    output_type=output_type,
                )
            )

    def _read_data(
        self,
        *,
        executor,
        output_type: OutputType,
    ) -> (
        pd.DataFrame | pl.DataFrame | list[RowMapping] | list[T] | RowMapping | T | None
    ):
        """
        Single source of truth for reading data from a connection.

        Args:
            executor: SQLAlchemy connection or session
            output_type: Output format for the returned data.
        """
        match output_type:
            case OutputType.POLARS:
                return self._read_polars(executor)
            case OutputType.PANDAS:
                return self._read_pandas(executor)
            case OutputType.SQLALCHEMY:
                return self._read_sqlalchemy(executor)
            case _:
                raise ValueError(f"Unsupported output_type: {output_type}")

    def _read_polars(self, executor) -> pl.DataFrame:
        conn = self._get_connection(executor)
        self._check_for_selectinload()
        df = pl.read_database(
            self._compile_query(conn),
            connection=conn,
            infer_schema_length=None,
        )
        return self._apply_mapping(df=df)

    def _read_pandas(self, executor) -> pd.DataFrame:
        conn = self._get_connection(executor)
        self._check_for_selectinload()
        df = pd.read_sql(
            self._compile_query(conn),
            con=conn,
        )
        df = self._apply_mapping(df=df)
        return self._normalize_pandas_dtypes(df=df)

    def _read_sqlalchemy(
        self, executor
    ) -> list[RowMapping] | list[T] | RowMapping | T | None:
        if isinstance(self.query, Select):
            if self.is_scalar:
                result = executor.execute(self.query)
                return result.scalars().unique().one_or_none()

            result = executor.execute(self.query.limit(_SQLALCHEMY_ROW_LIMIT))
            items = result.scalars().all()  # ORM return
            _raise_for_large_sqlalchemy_result(count=len(items))
            return items

        result = executor.execute(self.query)

        if self.is_scalar:
            return result.mappings().one_or_none()

        items = result.mappings().fetchmany(_SQLALCHEMY_ROW_LIMIT)
        _raise_for_large_sqlalchemy_result(count=len(items))
        return items

    def _get_connection(self, executor):
        """Extract the underlying connection from a session or connection object."""
        return (
            executor.connection()
            if hasattr(executor, "connection") and callable(executor.connection)
            else executor
        )

    def _get_sync_context(self, schema: str | None, output_type: OutputType):
        """Get the appropriate synchronous context manager."""
        if output_type == OutputType.SQLALCHEMY:
            return with_db(schema=schema)

        # Only set schema_translate_map when schema is provided.
        # Passing schema_translate_map=None still enables translation mode
        # and generates __[SCHEMA_x]__ placeholders that won't resolve.
        if schema:
            return engine.execution_options(
                schema_translate_map={"project": schema}
            ).connect()
        return engine.connect()

    def _get_async_context(self, schema: str | None, output_type: OutputType):
        """Get the appropriate asynchronous context manager."""
        if output_type == OutputType.SQLALCHEMY:
            return with_db_async(schema=schema)

        # Only set schema_translate_map when schema is provided.
        # Passing schema_translate_map=None still enables translation mode
        # and generates __[SCHEMA_x]__ placeholders that won't resolve.
        if schema:
            return async_engine.execution_options(
                schema_translate_map={"project": schema}
            ).connect()
        return async_engine.connect()

    def _compile_query(self, conn) -> str | Select | TextClause:
        """Helper to compile the query with the correct dialect and options."""
        if isinstance(self.query, TextClause):
            return self.query

        # Compile without schema_translate_map to get clean SQL with literal
        # schema names. Passing schema_translate_map to compile() generates
        # __[SCHEMA_x]__ placeholders for ALL schemas, not just mapped ones.
        compiled = self.query.compile(
            dialect=conn.dialect or postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
        sql = str(compiled)

        # Manually replace schema names if translation is needed
        schema_translate_map = conn.get_execution_options().get("schema_translate_map")
        if schema_translate_map:
            for source_schema, target_schema in schema_translate_map.items():
                if source_schema is not None and target_schema is not None:
                    # Replace schema references like "project.tablename"
                    sql = sql.replace(f"{source_schema}.", f"{target_schema}.")

        return sql

    def _check_for_selectinload(self) -> None:
        """
        Raise an error if selectinload is used in the query.

        selectinload executes multiple queries to load related objects,
        which doesn't work with pandas/polars since they only execute
        a single query. Users should use joinedload (single query with JOIN)
        or execute multiple DbQuery instances instead.
        """
        if not isinstance(self.query, Select):
            return

        for opt in self.query._with_options:
            if isinstance(opt, Load):
                for ctx_item in opt.context:
                    if isinstance(ctx_item, _LoadElement) and ctx_item.strategy == (
                        ("lazy", "selectin"),
                    ):
                        raise ValueError(
                            "selectinload cannot be used with pandas or polars "
                            "output types. selectinload executes multiple queries "
                            "to load related objects, but pandas/polars only "
                            "execute a single query. Use joinedload instead "
                            "(performs a JOIN in a single query) or execute "
                            "multiple DbQuery instances."
                        )

    def _apply_mapping(self, *, df: pd.DataFrame | pl.DataFrame):
        """
        Standardize column names across all dataframe types.

        Args:
            df: DataFrame to rename if mapped columns are present.
        """
        cols = {k: v for k, v in _SQL_TO_MODEL_COL_MAP.items() if k in df.columns}
        return (
            df.rename(columns=cols) if isinstance(df, pd.DataFrame) else df.rename(cols)
        )

    def _normalize_pandas_dtypes(
        self,
        *,
        df: pd.DataFrame,
        strings_as_object: bool = True,
    ) -> pd.DataFrame:
        """
        Convert Arrow-backed dtypes to pandas/numpy dtypes for
        compatibility with legacy code.

        - First: Arrow -> pandas nullable (Int64, Float64, boolean, string)
        - Then: if no NA present, nullable ints -> int64, bools -> bool
        - Optionally: strings -> object (many libs expect object dtype)

        Args:
            df: DataFrame to normalize
            strings_as_object: Convert string columns to object dtype
        """
        # Fast path: only do work if any Arrow dtype present
        if any(getattr(dt, "pyarrow_dtype", None) is not None for dt in df.dtypes):
            # Arrow -> pandas nullable dtypes
            df = df.convert_dtypes(dtype_backend="numpy_nullable")

        # Downcast nullable integers/bools without NA to plain numpy dtypes
        for col in df.columns:
            s = df[col]
            dt = s.dtype
            if pdt.is_integer_dtype(dt) and not s.isna().any():
                df[col] = s.astype("int64")
            elif pdt.is_bool_dtype(dt) and not s.isna().any():
                df[col] = s.astype("bool")

        # Optionally coerce pandas StringDtype -> object for max compat
        if strings_as_object:
            str_cols = df.select_dtypes(include=["string"]).columns
            if len(str_cols) > 0:
                df[str_cols] = df[str_cols].astype("object")

        return df


def postprocess_pandas_df(
    *,
    df: pd.DataFrame,
    index: str | None = None,
    as_datetime: bool = False,
    tz: str | None = None,
) -> pd.DataFrame:
    """
    Apply optional index, datetime, and timezone normalization.

    Args:
        df: DataFrame to postprocess.
        index: Column name to set as the index.
        as_datetime: Convert the index column to datetime when True.
        tz: Timezone to localize/convert when as_datetime is True.
    """
    if index:
        if index not in df.columns:
            raise ValueError(f"Column '{index}' not found in DataFrame.")
        if as_datetime:
            df[index] = pd.to_datetime(df[index], errors="coerce")
            if tz:
                if getattr(df[index].dt, "tz", None) is None:
                    df[index] = df[index].dt.tz_localize(
                        "UTC",
                        nonexistent="NaT",
                        ambiguous="NaT",
                    )
                df[index] = df[index].dt.tz_convert(tz)
        elif tz:
            warnings.warn(
                "tz is only valid when as_datetime=True.",
                category=RuntimeWarning,
                stacklevel=2,
            )
        df = df.set_index(index)
    elif as_datetime or tz:
        warnings.warn(
            "as_datetime and tz require index to be defined.",
            category=RuntimeWarning,
            stacklevel=2,
        )
    return df
