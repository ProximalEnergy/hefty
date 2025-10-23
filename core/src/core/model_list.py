"""Model list and item wrappers for SQLAlchemy queries with Polars and Pandas support."""

import asyncio
import warnings
from collections.abc import Iterable, Iterator
from typing import Any, TypeVar, cast

import pandas as pd
import polars as pl
import sqlalchemy as sa
from sqlalchemy import TextClause, create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Result
from sqlalchemy.inspection import inspect
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import (
    Mapper,
    Query,
    class_mapper,
)
from sqlalchemy.orm.exc import UnmappedClassError

from core.database import database_url

T = TypeVar("T")


class UninitializedError(Exception):
    """Exception raised when item(s) are not loaded."""


UNINITIALIZED_ERROR_ITEM = UninitializedError(
    "Item is not loaded. Call ModelItem.query_item() to load item."
)

UNINITIALIZED_ERROR_ITEMS = UninitializedError(
    "Items are not loaded. Call ModelList.query_items() to load items."
)


class MissingQueryError(Exception):
    """Exception raised when a SQLAlchemy ORM query is expected but missing."""


MISSING_QUERY_ERROR = MissingQueryError(
    "Query is not available. This ModelList was initialized with a raw SQL result, "
    "so certain functions such as `.query_items()` and `.sql_string()` are unsupported."
)


def _sql_string[T](*, query: Query[T]) -> str:
    if not hasattr(query, "statement"):
        raise ValueError("The query does not support SQL compilation.")

    # Try to extract schema_translate_map from the session's bind
    schema_translate_map: dict[str, str] | None = None
    session = query.session
    if session and hasattr(session, "bind") and session.bind:
        execution_options = getattr(session.bind, "_execution_options", {})
        schema_translate_map = execution_options.get("schema_translate_map")

    # Compile the query
    compiled = query.statement.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )

    sql = str(compiled)

    if schema_translate_map:
        for key, value in schema_translate_map.items():
            sql = sql.replace(key, value)

    return sql


class ModelList[T]:
    """
    Purpose
    -------
    Wraps a SQLAlchemy query that returns one or more rows. Can either execute
    immediately (via `query.all()`) or defer execution to external query engines like
    Polars.

    Initialization
    --------------
    `ml = ModelList(query=query(MyModel), return_query=False)`
    - If `return_query=False` (default), executes query immediately and stores in
      `.items`.
    - If `return_query=True`, query is stored unexecuted for alternative usage.

    Accessing Models
    ----------------
    - `ml.models()`         # List of SQLAlchemy model instances (after execution)
    - `ml[i]`               # Access a model by index
    - `len(ml)`             # Number of items
    - `for item in ml: ...` # Iterate over items

    Generating a Pandas DataFrame
    -----------------------------
    `ml.pandas_dataframe(index='created_at', as_datetime=True, tz='UTC')`
    - Converts the loaded models into a Pandas DataFrame
    - Can set an index column and localize to a timezone

    Using Polars Instead of SQLAlchemy
    -----------------------------
    `await ml.polars_dataframe()`
    - Recommended when `return_query=True` and items have not yet been loaded.

    SQL Introspection
    -----------------
    `ml.sql_string()`     # Returns the compiled SQL string with literal parameters

    Warnings
    --------
    - Raises `UninitializedError` if attempting to access items before query execution.
    - Emits `RuntimeWarning` if Polars is used after SQLAlchemy execution.
    """

    _sql_to_model_col_map = {"time_bucket": "time"}

    def __init__(
        self,
        *,
        query: Query[T] | TextClause | None = None,
        result: Result | None = None,
        model_cls: type[T] | None = None,
        return_query: bool = False,
    ):
        if query is not None:
            self.query: Query[T] | TextClause | None = query
            self.items: list[T] | None = (
                None if return_query or isinstance(query, TextClause) else query.all()
            )
        elif result is not None and model_cls is not None:
            self.query = None  # No ORM query
            # Manually map the result to the model class
            self.items = []
            for row in result:
                mapped_data = {}
                for k, v in row._mapping.items():
                    mapped_key = self._sql_to_model_col_map.get(k, k)
                    mapped_data[mapped_key] = v
                self.items.append(model_cls(**mapped_data))
        else:
            raise ValueError(
                "Either 'query' or ('result' and 'model_cls') must be provided."
            )

    def __iter__(self) -> Iterator[T]:
        if self.items is None:
            raise UNINITIALIZED_ERROR_ITEMS

        return iter(self.items)

    def __getitem__(self, index: int) -> T:  # skip-star-syntax
        if self.items is None:
            raise UNINITIALIZED_ERROR_ITEMS

        return self.items[index]

    def __len__(self) -> int:
        if self.items is None:
            raise UNINITIALIZED_ERROR_ITEMS

        return len(self.items)

    def query_items(self) -> None:
        """Execute query and store the results in `.items`."""
        if self.query is None:
            raise MISSING_QUERY_ERROR
        elif isinstance(self.query, Query):
            self.items = self.query.all()
        elif isinstance(self.query, TextClause):
            raise TypeError(
                "Converting TextClause to .items has not been implemented."
                "Please feel free to add this functionality if you would like."
            )
        else:
            raise TypeError("query must be an instance of Query")

    def sql_string(self) -> str:
        """Return the raw SQL string of the underlying SQLAlchemy query."""
        if self.query is None:
            raise MISSING_QUERY_ERROR
        elif isinstance(self.query, Query):
            return _sql_string(query=self.query)
        elif isinstance(self.query, TextClause):
            return str(self.query)
        else:
            raise TypeError("query must be an instance of Query | TextClause")

    def models(self) -> list[T]:
        """Return a list of SQLAlchemy model instances."""
        if self.items is None:
            raise UNINITIALIZED_ERROR_ITEMS

        return self.items

    def pandas_dataframe(
        self,
        *,
        index: str | None = None,
        as_datetime: bool = False,
        tz: str | None = None,
    ) -> pd.DataFrame:
        """Convert the loaded models into a Pandas DataFrame."""
        if self.items is None:
            # Handle TextClause queries by executing them directly
            if isinstance(self.query, TextClause):
                from sqlalchemy import create_engine

                from core.database import database_url

                engine = create_engine(database_url())
                with engine.connect() as connection:
                    df = pd.read_sql(
                        sql=self.query,
                        con=connection,
                    )
                    # Apply column mapping for consistency with model-based results
                    if self._sql_to_model_col_map:
                        df = df.rename(columns=self._sql_to_model_col_map)
            else:
                raise UNINITIALIZED_ERROR_ITEMS
        else:
            if len(self.items) == 0:
                return pd.DataFrame()

            df = pd.DataFrame(
                [
                    {
                        col.key: getattr(obj, col.key)
                        for col in inspect(obj).mapper.column_attrs  # type: ignore
                    }
                    for obj in self.items
                ]
            )

        if index:
            if index not in df.columns:
                raise ValueError(f"Column '{index}' not found in DataFrame.")
            if as_datetime:
                df[index] = pd.to_datetime(df[index], errors="coerce")
                if tz:
                    if df[index].dt.tz is None:
                        df[index] = df[index].dt.tz_localize(
                            "UTC", nonexistent="NaT", ambiguous="NaT"
                        )
                    df[index] = df[index].dt.tz_convert(tz)
            elif tz:
                warnings.warn(
                    "tz is only a valid input when as_datetime=True.",
                    category=RuntimeWarning,
                    stacklevel=2,
                )
            df = df.set_index(index)
        elif as_datetime or tz:
            warnings.warn(
                "as_datetime and tz are only valid inputs when index is defined.",
                category=RuntimeWarning,
                stacklevel=2,
            )

        return df

    async def polars_dataframe_async(self) -> pl.DataFrame:
        """Run the query using Polars instead of SQLAlchemy and return a Polars DataFrame."""
        if self.items is not None:
            warnings.warn(
                """
                ModelList.polars_dataframe() is inefficient when items are already
                loaded. Best practice is to use ModelItem.polars_dataframe() when
                return_query=True.
                """,
                category=RuntimeWarning,
                stacklevel=2,
            )

        def _run_query() -> pl.DataFrame:
            engine = create_engine(database_url())
            with engine.connect() as connection:
                # For TextClause objects, pass the query object directly
                # so Polars can handle the bound parameters properly
                if isinstance(self.query, TextClause):
                    df = pl.read_database(
                        query=self.query,
                        connection=connection,
                        infer_schema_length=None,
                    )
                    # Apply column mapping for consistency with model-based results
                    if self._sql_to_model_col_map:
                        # Only rename columns that actually exist in the dataframe
                        cols_to_rename = {
                            k: v
                            for k, v in self._sql_to_model_col_map.items()
                            if k in df.columns
                        }
                        if cols_to_rename:
                            df = df.rename(cols_to_rename)
                else:
                    df = pl.read_database(
                        query=self.sql_string(),
                        connection=connection,
                        infer_schema_length=None,
                    )
            return df

        # Run the blocking database operation in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run_query)

    @classmethod
    def from_items(cls, items: list[T]) -> "ModelList[T]":  # skip-star-syntax
        """
        Construct a ModelList directly from an in-memory list of model instances.
        Avoids needing query/result/model_cls.
        """
        inst = cls.__new__(cls)  # bypass __init__
        inst.query = None
        inst.items = items
        return inst

    def find(self, /, **criteria: Any) -> "ModelList[T]":
        """
        Return a new ModelList filtered by the given criteria.

        Supported operators:
        - field=val        -> equality
        - field__ne=val    -> !=
        - field__gt=val    -> >
        - field__lt=val    -> <
        - field__ge=val    -> >=
        - field__le=val    -> <=
        - field__in=[...]  -> IN

        Also supported (optional sugar):
        - field=[...]      -> IN (if value is a non-string iterable)

        Examples:
            tags.find(tag_id=123)
            tags.find(tag_id__in=[123, 456])
            devices.find(device_type_id__ne=2)
            devices.find(created_at__gt="2025-01-01")
        """
        # --- QA ---
        if isinstance(self.query, TextClause):
            raise TypeError(
                "Find is not implemented for TextClause."
                "Please feel free to contribute this functionality"
            )

        # --- Constants ---
        SUPPORTED_OPS = {"eq", "ne", "gt", "lt", "ge", "le", "in"}

        # --- Internal Functions ---
        def _is_iterable_but_not_string(x: object) -> bool:  # skip-star-syntax
            return isinstance(x, Iterable) and not isinstance(
                x, (str, bytes, bytearray)
            )

        def _normalize_criteria(  # skip-star-syntax
            raw: dict[str, Any],
        ) -> list[tuple[str, str, Any]]:
            """Normalize criteria into (field, op, value)."""
            norm: list[tuple[str, str, Any]] = []
            for key, val in raw.items():
                if "__" in key:
                    field, op = key.split("__", 1)
                    if op not in SUPPORTED_OPS:
                        raise ValueError(
                            f"Unsupported operator '__{op}' in find() for key '{key}'."
                        )
                    if op == "in":
                        if not _is_iterable_but_not_string(val):
                            raise ValueError(
                                f"Value for '{key}' must be a non-string iterable."
                            )
                    norm.append((field, op, val))
                else:
                    # No suffix: equality, unless value looks like an IN iterable
                    if _is_iterable_but_not_string(val):
                        norm.append((key, "in", val))
                    else:
                        norm.append((key, "eq", val))
            return norm

        normalized = _normalize_criteria(criteria)

        # Short-circuit: empty IN → return nothing
        for _, op, v in normalized:
            if op == "in" and len(tuple(v)) == 0:
                return ModelList.from_items([])

        # Case A: deferred query → push to SQL
        if self.items is None and self.query is not None:
            descs = getattr(self.query, "column_descriptions", None)
            if not descs:
                raise ValueError("find() requires an ORM query with a primary entity.")
            entity = descs[0].get("entity")
            if entity is None:
                raise ValueError("find() requires an ORM query with a primary entity.")

            mapper = sa_inspect(entity)
            col_keys = set(mapper.columns.keys())

            invalid = [field for field, _, _ in normalized if field not in col_keys]
            if invalid:
                raise ValueError(
                    f"Unknown column(s) for {mapper.class_.__name__} in find(): {invalid}"
                )

            exprs: list[Any] = []
            for field, op, value in normalized:
                col = mapper.columns[field]
                if op == "eq":
                    exprs.append(col == value)
                elif op == "ne":
                    exprs.append(col != value)
                elif op == "gt":
                    exprs.append(col > value)
                elif op == "lt":
                    exprs.append(col < value)
                elif op == "ge":
                    exprs.append(col >= value)
                elif op == "le":
                    exprs.append(col <= value)
                elif op == "in":
                    seq = tuple(value)
                    exprs.append(sa.false() if len(seq) == 0 else col.in_(seq))
            new_q = self.query.filter(sa.and_(*exprs))
            return ModelList(query=new_q, return_query=True)

        # Case B: in-memory filtering
        if self.items is not None:
            if len(self.items) > 0:
                mapper = sa_inspect(self.items[0]).mapper  # type: ignore[arg-type, union-attr]
                col_keys = set(mapper.columns.keys())
                invalid = [field for field, _, _ in normalized if field not in col_keys]
                if invalid:
                    raise ValueError(
                        f"Unknown attribute(s) for {mapper.class_.__name__} in find(): {invalid}"
                    )

            def _match(obj: Any) -> bool:  # skip-star-syntax
                for field, op, value in normalized:
                    attr = getattr(obj, field)
                    if op == "eq" and not (attr == value):
                        return False
                    elif op == "ne" and not (attr != value):
                        return False
                    elif op == "gt" and not (attr > value):
                        return False
                    elif op == "lt" and not (attr < value):
                        return False
                    elif op == "ge" and not (attr >= value):
                        return False
                    elif op == "le" and not (attr <= value):
                        return False
                    elif op == "in" and attr not in set(value):
                        return False
                return True

            filtered = [obj for obj in self.items if _match(obj)]
            return ModelList.from_items(filtered)

        raise UNINITIALIZED_ERROR_ITEMS


class ModelItem[T]:
    """
    Purpose
    -------
    Wraps a SQLAlchemy query expected to return a single row (via `query.first()`).
    Can also defer execution for use with alternative engines like Polars.

    Initialization
    --------------
    `mi = ModelItem(query=session.query(MyModel).filter(...), return_query=False)`
    - If `return_query=False` (default), executes query immediately and stores in
      `.item`.
    - If `return_query=True`, query is stored unexecuted for alternative usage.

    Accessing the Model
    -------------------
    - `mi.model()`          # Returns the single SQLAlchemy model instance
    - `mi.to_dict()`        # Converts the model to a flat dictionary of columns
    - `mi.pandas_series()`  # Converts the model to a Pandas Series
    - `mi.pandas_dataframe(index='created_at', as_datetime=True, tz='UTC')`
                         # Converts to a one-row Pandas DataFrame

    Using Polars Instead of SQLAlchemy
    -----------------------------
    - `await mi.polars_dataframe()`  # Returns the full result as a Polars DataFrame
    - `mi.polars_series()`     # Returns the first row of the query as a Polars Series
    - Only valid when return_query=True and item has not yet been loaded

    SQL Introspection
    -----------------
    - `mi.sql_string()`     # Returns the compiled SQL string with bound parameters

    Warnings
    --------
    - Raises `UninitializedError` if attempting to access the item before query execution.
    - Emits `RuntimeWarning` if Polars is used after SQLAlchemy execution.
    """

    def __init__(self, *, query: Query[T], return_query: bool = False):
        self.query: Query[T] = query
        self.item: T | None = None if return_query else query.first()

    def query_item(self) -> None:
        """Execute query and store the result in `.item`."""
        self.item = self.query.first()

    def sql_string(self) -> str:
        """Return the raw SQL string of the underlying SQLAlchemy query."""
        return _sql_string(query=self.query)

    def dictionary(self) -> dict[str, Any]:
        """Return the model as a dictionary."""
        if self.item is None:
            raise UNINITIALIZED_ERROR_ITEM

        try:
            mapper: Mapper = class_mapper(self.item.__class__)
        except UnmappedClassError:
            raise TypeError(f"{self.item!r} is not a SQLAlchemy-mapped instance.")

        return {col.key: getattr(self.item, col.key) for col in mapper.column_attrs}

    def model(self) -> T:
        """Return a SQLAlchemy model instance."""
        if self.item is None:
            raise UNINITIALIZED_ERROR_ITEM

        return self.item

    def pandas_series(self) -> pd.Series:
        """Return a Pandas Series of the model."""
        if self.item is None:
            raise UNINITIALIZED_ERROR_ITEM

        try:
            mapper: Mapper = class_mapper(self.item.__class__)
        except UnmappedClassError:
            raise TypeError(f"{self.item!r} is not a SQLAlchemy-mapped instance.")

        row = {col.key: getattr(self.item, col.key) for col in mapper.column_attrs}

        return cast(pd.Series, pd.Series(row))

    def pandas_dataframe(
        self,
        *,
        index: str | None = None,
        as_datetime: bool = False,
        tz: str | None = None,
    ) -> pd.DataFrame:
        """Convert the model to a Pandas DataFrame."""
        if self.item is None:
            raise UNINITIALIZED_ERROR_ITEM

        try:
            mapper: Mapper = class_mapper(self.item.__class__)
        except UnmappedClassError:
            raise TypeError(f"{self.item!r} is not a SQLAlchemy-mapped instance.")

        row = {col.key: getattr(self.item, col.key) for col in mapper.column_attrs}

        df = pd.DataFrame([row])

        if index:
            if index not in df.columns:
                raise ValueError(f"Column '{index}' not found in DataFrame.")
            if as_datetime:
                df[index] = pd.to_datetime(df[index], errors="coerce")
                if tz:
                    df[index] = (
                        df[index]
                        .dt.tz_localize("UTC", nonexistent="NaT", ambiguous="NaT")
                        .dt.tz_convert(tz)
                    )
            df = df.set_index(index)

        return df

    async def polars_dataframe(self) -> pl.DataFrame:
        """
        Execute the stored query using Polars instead of SQLAlchemy.

        Returns:
            A Polars DataFrame representing the result of the query.

        Warns:
            RuntimeWarning if the item is already loaded.
        """
        if self.item is not None:
            warnings.warn(
                """
                ModelItem.polars_dataframe() is inefficient when item is already loaded.
                Consider using this method only when return_query=True.
                """,
                category=RuntimeWarning,
                stacklevel=2,
            )

        def _run_query() -> pl.DataFrame:
            engine = create_engine(database_url())
            with engine.connect() as conn:
                df = pl.read_database(self.sql_string(), conn)
            return df

        # Run the blocking database operation in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run_query)
