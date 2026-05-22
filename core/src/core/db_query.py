"""Database query wrapper for efficient Polars and Pandas dataframe operations."""

import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeVar

import pandas as pd
import polars as pl
from pandas.api import types as pdt
from sqlalchemy import Select, TextClause
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm.strategy_options import Load, _LoadElement
from sqlalchemy.sql.elements import Label
from sqlalchemy.sql.expression import Executable
from sqlalchemy.sql.functions import FunctionElement

from core.database import async_engine, engine, with_db, with_db_async

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
    from sqlalchemy.orm import Session

T = TypeVar("T")
S = TypeVar(
    "S",
    bound=Literal[True] | Literal[False],
)
_SQL_TO_MODEL_COL_MAP: Mapping[str, str] = {"time_bucket": "time"}
_SQLALCHEMY_ROW_THRESHOLD = 100


def _warn_for_large_sqlalchemy_result(*, count: int) -> None:
    if count >= _SQLALCHEMY_ROW_THRESHOLD:
        warnings.warn(
            "Too many SQLAlchemy rows (>=100). Use pandas or polars instead.",
            category=RuntimeWarning,
            stacklevel=2,
        )


from core.enumerations import OutputType as OutputType


@dataclass
class DbQuery[T, S]:
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

    query: TextClause | Select | Executable
    is_scalar: bool = False

    def get(
        self,
        *,
        executor: "Connection | Session | None" = None,
        schema: str | None = "operational",
        output_type: OutputType = OutputType.POLARS,
    ) -> (
        pd.DataFrame | pl.DataFrame | list[RowMapping] | list[T] | RowMapping | T | None
    ):
        """
        Execute the query on a sync connection and return data.

        Args:
            executor: Optional external session/connection.
            schema: Optional schema name for translation map.
            output_type: Output format for the returned data.
        """
        if executor:
            return self._read_data(
                executor=executor,
                output_type=output_type,
            )

        with self._get_sync_context(schema=schema, output_type=output_type) as db_obj:
            return self._read_data(
                executor=db_obj,
                output_type=output_type,
            )

    async def get_async(
        self,
        *,
        executor: "AsyncConnection | AsyncSession | None" = None,
        schema: str | None = "operational",
        output_type: OutputType = OutputType.POLARS,
    ) -> (
        pd.DataFrame | pl.DataFrame | list[RowMapping] | list[T] | RowMapping | T | None
    ):
        """
        Execute the query on an async connection and return data.

        Args:
            executor: Optional external async session/connection.
            schema: Optional schema name for translation map.
            output_type: Output format for the returned data.
        """
        if executor:
            return await executor.run_sync(
                lambda sync_obj: self._read_data(
                    executor=sync_obj,
                    output_type=output_type,
                )
            )

        async with self._get_async_context(
            schema=schema, output_type=output_type
        ) as db_obj:
            return await db_obj.run_sync(
                lambda sync_obj: self._read_data(
                    executor=sync_obj,
                    output_type=output_type,
                )
            )

    def execute(
        self,
        *,
        executor: "Connection | Session | None" = None,
        schema: str | None = "operational",
    ) -> None:
        """
        Execute a write operation (INSERT/UPDATE/DELETE).
        Commits if managing its own session.

        Args:
            executor: Optional external session/connection.
            schema: Optional schema name for translation map.
        """
        if executor:
            executor.execute(self.query)
            return

        with self._get_sync_context(
            schema=schema, output_type=OutputType.SQLALCHEMY
        ) as db:
            db.execute(self.query)
            db.commit()

    async def execute_async(
        self,
        *,
        executor: "AsyncConnection | AsyncSession | None" = None,
        schema: str | None = "operational",
    ) -> None:
        """
        Execute a write operation (INSERT/UPDATE/DELETE) asynchronously.
        Commits if managing its own session.

        Args:
            executor: Optional external async session/connection.
            schema: Optional schema name for translation map.
        """
        if executor:
            await executor.execute(self.query)
            return

        async with self._get_async_context(
            schema=schema, output_type=OutputType.SQLALCHEMY
        ) as db:
            await db.execute(self.query)
            await db.commit()

    def _read_data(
        self,
        *,
        executor: Any,
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
                return self._read_polars(executor=executor)
            case OutputType.PANDAS:
                return self._read_pandas(executor=executor)
            case OutputType.SQLALCHEMY:
                return self._read_sqlalchemy(executor=executor)
            case _:
                raise ValueError(f"Unsupported output_type: {output_type}")

    def _read_polars(self, *, executor) -> pl.DataFrame:
        conn = self._get_connection(executor=executor)
        self._check_for_selectinload()
        df = pl.read_database(
            self._compile_query(conn=conn),
            connection=conn,
            infer_schema_length=None,
        )
        return self._apply_mapping(df=df)

    def _read_pandas(self, *, executor) -> pd.DataFrame:
        conn = self._get_connection(executor=executor)
        self._check_for_selectinload()
        df = pd.read_sql(
            self._compile_query(conn=conn),
            con=conn,
        )
        df = self._apply_mapping(df=df)
        return self._normalize_pandas_dtypes(df=df)

    def _read_sqlalchemy(
        self, *, executor
    ) -> list[RowMapping] | list[T] | RowMapping | T | None:
        if isinstance(self.query, Select):
            if self.is_scalar:
                result = executor.execute(self.query)
                if self._select_returns_rows() or self._select_returns_mapping():
                    return result.mappings().one_or_none()
                return result.scalars().unique().one_or_none()

            result = executor.execute(self.query)
            if self._select_returns_rows():
                items = result.all()  # Row return
            else:
                items = result.scalars().all()  # ORM or scalar return

            _warn_for_large_sqlalchemy_result(count=len(items))
            return items

        result = executor.execute(self.query)

        if getattr(result, "returns_rows", True) is False:
            return None

        if self.is_scalar:
            return result.mappings().one_or_none()

        items = result.mappings().all()
        _warn_for_large_sqlalchemy_result(count=len(items))
        return items

    def _select_returns_rows(self) -> bool:
        """Determine whether SQLAlchemy output should return rows."""
        return (
            isinstance(self.query, Select) and len(self.query.column_descriptions) != 1
        )

    def _select_returns_mapping(self) -> bool:
        """Determine whether a scalar SQLAlchemy read should return a mapping."""
        if not isinstance(self.query, Select):
            return False

        if len(self.query.column_descriptions) != 1:
            return False

        expr = self.query.column_descriptions[0].get("expr")
        return isinstance(expr, Label) and not isinstance(expr.element, FunctionElement)

    def _get_connection(self, *, executor):
        """Extract the underlying connection from a session or connection object.

        Args:
            executor: A SQLAlchemy session or connection object.
        """
        return (
            executor.connection()
            if hasattr(executor, "connection") and callable(executor.connection)
            else executor
        )

    def _get_sync_context(self, *, schema: str | None, output_type: OutputType):
        """Get the appropriate synchronous context manager.

        Args:
            schema: Optional database schema name to set on the connection.
            output_type: Determines whether to return a SQLAlchemy session or
                a raw engine connection.
        """
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

    def _get_async_context(self, *, schema: str | None, output_type: OutputType):
        """Get the appropriate asynchronous context manager.

        Args:
            schema: Optional database schema name to set on the connection.
            output_type: Determines whether to return a SQLAlchemy session or
                a raw async engine connection.
        """
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

    def _compile_query(self, *, conn) -> str | Select | TextClause:
        """Helper to compile the query with the correct dialect and options.

        Args:
            conn: Active database connection supplying the dialect and
                execution options (e.g. schema_translate_map).
        """
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
