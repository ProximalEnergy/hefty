from __future__ import annotations

import inspect
import types
from typing import Any, Union, get_args, get_origin

import xarray as xr
from kpi_pipeline.base.models import CoordCombinerModel
from kpi_pipeline.base.protocols import CoordCombinerProtocol
from pydantic.fields import PydanticUndefined

# Function parameters that may be skipped when comparing against the calc
DEFAULT_FUNCTION_IGNORES = {
    "time_zone",
}
# Function parameter annotations that may be skipped when comparing against the calc
# Note: CoordCombinerProtocol is handled specially - it must map to CoordCombinerModel
DEFAULT_FUNCTION_TYPE_IGNORES: set[type] = set()
# Calc constructor parameters that may be skipped when comparing against the function
DEFAULT_CALC_IGNORES = {
    "output_dtype",
}


def _snake_to_camel(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def _is_data_array_type(annotation: Any) -> bool:
    if annotation is xr.DataArray:
        return True
    origin = get_origin(annotation)
    if origin is None:
        return False
    return any(_is_data_array_type(arg) for arg in get_args(annotation))


def _annotation_str(annotation: Any) -> str:
    if annotation is inspect._empty:
        return "<unspecified>"
    if hasattr(annotation, "__name__"):
        return str(annotation.__name__)
    return repr(annotation)


def _types_match(expected: Any, actual: Any) -> bool:
    if expected is inspect._empty or actual is inspect._empty:
        return expected is actual
    if expected == actual:
        return True
    expected_origin, actual_origin = get_origin(expected), get_origin(actual)
    if expected_origin is not None and actual_origin is not None:
        union_origins = (Union, types.UnionType)
        same_origin = expected_origin == actual_origin
        both_unions = (
            expected_origin in union_origins and actual_origin in union_origins
        )
        if same_origin or both_unions:
            return set(get_args(expected)) == set(get_args(actual))
    return False


def _annotation_matches_ignore(annotation: Any, ignored_types: set[type]) -> bool:
    if annotation is inspect._empty or not ignored_types:
        return False
    if annotation in ignored_types:
        return True
    origin = get_origin(annotation)
    if origin and origin in ignored_types:
        return True
    return any(
        _annotation_matches_ignore(arg, ignored_types) for arg in get_args(annotation)
    )


def _is_coord_combiner_protocol(annotation: Any) -> bool:
    """Check if annotation is CoordCombinerProtocol."""
    if annotation is CoordCombinerProtocol:
        return True
    origin = get_origin(annotation)
    if origin is CoordCombinerProtocol:
        return True
    return any(_is_coord_combiner_protocol(arg) for arg in get_args(annotation))


def _is_optional_coord_combiner_protocol(annotation: Any) -> bool:
    """Check if annotation is Optional[CoordCombinerProtocol]."""
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        args = get_args(annotation)
        if len(args) == 2 and type(None) in args:
            other_arg = next((arg for arg in args if arg is not type(None)), None)
            return other_arg is not None and _is_coord_combiner_protocol(other_arg)
    return False


def _is_optional_data_array(annotation: Any) -> bool:
    """Check if annotation is Optional[xr.DataArray] or Union[xr.DataArray, None]."""
    origin = get_origin(annotation)
    # Handle both Union (old syntax) and types.UnionType (| syntax)
    if origin in (Union, types.UnionType):
        args = get_args(annotation)
        if len(args) == 2 and type(None) in args:
            other_arg = next((arg for arg in args if arg is not type(None)), None)
            return other_arg is not None and _is_data_array_type(other_arg)
    return False


def _collect_function_params(
    func, ignores: set[str], type_ignores: set[type]
) -> dict[str, tuple[Any, Any]]:
    sig = inspect.signature(func)
    params: dict[str, tuple[Any, Any]] = {}
    for name, param in sig.parameters.items():
        if name in ignores:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if _annotation_matches_ignore(param.annotation, type_ignores):
            continue
        params[name] = (
            param.annotation
            if param.annotation is not inspect._empty
            else inspect._empty,
            param.default if param.default is not inspect._empty else inspect._empty,
        )
    return params


def _collect_calc_params(calc_cls, ignores: set[str]) -> dict[str, tuple[Any, Any]]:
    # Prefer Pydantic model fields if available to capture declared defaults and annotations.
    if hasattr(calc_cls, "model_fields"):
        params: dict[str, tuple[Any, Any]] = {}
        for name, field in calc_cls.model_fields.items():
            if name in ignores:
                continue
            default = (
                field.default
                if field.default is not PydanticUndefined
                else inspect._empty
            )
            params[name] = (field.annotation, default)
        return params

    sig = inspect.signature(calc_cls.__init__)
    params = {}
    for name, param in sig.parameters.items():
        if name == "self" or name in ignores:
            continue
        params[name] = (
            param.annotation
            if param.annotation is not inspect._empty
            else inspect._empty,
            param.default if param.default is not inspect._empty else inspect._empty,
        )
    return params


def verify_calc_function_alignment(
    calc_cls,
    func,
    *,
    function_ignores: set[str] | None = None,
    function_type_ignores: set[type] | None = None,
    calc_ignores: set[str] | None = None,
) -> list[str]:
    """
    Verify that a Calc class and a domain function align on parameter names, types, and defaults.
    """
    function_ignores = set(function_ignores or DEFAULT_FUNCTION_IGNORES)
    function_type_ignores = set(function_type_ignores or DEFAULT_FUNCTION_TYPE_IGNORES)
    calc_ignores = set(calc_ignores or DEFAULT_CALC_IGNORES)

    issues: list[str] = []
    func_params = _collect_function_params(
        func, function_ignores, function_type_ignores
    )
    calc_params = _collect_calc_params(calc_cls, calc_ignores)

    expected_class_name = f"{_snake_to_camel(func.__name__)}Calc"
    if calc_cls.__name__ != expected_class_name:
        issues.append(
            f"Class name '{calc_cls.__name__}' should be '{expected_class_name}' derived from '{func.__name__}'."
        )

    matched_calc_params: set[str] = set()
    for func_name, (func_ann, func_default) in func_params.items():
        expected_name = func_name
        expected_ann = func_ann

        # Special handling for CoordCombinerProtocol -> CoordCombinerModel mapping
        if _is_optional_coord_combiner_protocol(func_ann):
            expected_name = f"{func_name}_model"
            expected_ann = CoordCombinerModel | None
        elif _is_coord_combiner_protocol(func_ann):
            expected_name = f"{func_name}_model"
            expected_ann = CoordCombinerModel
        elif _is_optional_data_array(func_ann):
            expected_name = f"{func_name}_var"
            expected_ann = str | None
        elif _is_data_array_type(func_ann):
            expected_name = f"{func_name}_var"
            expected_ann = str

        if expected_name not in calc_params:
            issues.append(
                f"Missing calc parameter '{expected_name}' mapped from function parameter '{func_name}'."
            )
            continue

        calc_ann, calc_default = calc_params[expected_name]
        matched_calc_params.add(expected_name)

        if not _types_match(expected_ann, calc_ann):
            issues.append(
                f"Type mismatch for '{expected_name}': function expects {_annotation_str(expected_ann)}, "
                f"calc defines {_annotation_str(calc_ann)}."
            )

        defaults_match = (
            func_default is inspect._empty
            and calc_default is inspect._empty
            or func_default == calc_default
        )
        if not defaults_match:
            issues.append(
                f"Default mismatch for '{expected_name}': function has {func_default!r}, calc has {calc_default!r}."
            )

    extra_calc_params = set(calc_params) - matched_calc_params
    for name in sorted(extra_calc_params):
        issues.append(f"Calc parameter '{name}' has no counterpart in the function.")

    return issues


# Process function alignment checking

# Function parameters that may be skipped when comparing against the process
DEFAULT_PROCESS_FUNCTION_IGNORES = {
    "x",  # x is always passed directly, not as a parameter
    "time_zone",
}
# Process constructor parameters that may be skipped when comparing against the function
DEFAULT_PROCESS_IGNORES = {
    # context is always present in __call__ but not in domain function
}


def _collect_process_params(
    process_cls, ignores: set[str]
) -> dict[str, tuple[Any, Any]]:
    # Prefer Pydantic model fields if available to capture declared defaults and annotations.
    if hasattr(process_cls, "model_fields"):
        params: dict[str, tuple[Any, Any]] = {}
        for name, field in process_cls.model_fields.items():
            if name in ignores:
                continue
            default = (
                field.default
                if field.default is not PydanticUndefined
                else inspect._empty
            )
            params[name] = (field.annotation, default)
        return params

    sig = inspect.signature(process_cls.__init__)
    params = {}
    for name, param in sig.parameters.items():
        if name == "self" or name in ignores:
            continue
        params[name] = (
            param.annotation
            if param.annotation is not inspect._empty
            else inspect._empty,
            param.default if param.default is not inspect._empty else inspect._empty,
        )
    return params


def verify_process_function_alignment(
    process_cls,
    func,
    *,
    function_ignores: set[str] | None = None,
    function_type_ignores: set[type] | None = None,
    process_ignores: set[str] | None = None,
) -> list[str]:
    """
    Verify that a Process class and a domain function align on parameter names, types, and defaults.
    """
    function_ignores = set(function_ignores or DEFAULT_PROCESS_FUNCTION_IGNORES)
    function_type_ignores = set(function_type_ignores or DEFAULT_FUNCTION_TYPE_IGNORES)
    process_ignores = set(process_ignores or DEFAULT_PROCESS_IGNORES)

    issues: list[str] = []
    func_params = _collect_function_params(
        func, function_ignores, function_type_ignores
    )
    process_params = _collect_process_params(process_cls, process_ignores)

    expected_class_name = f"{_snake_to_camel(func.__name__)}Process"
    if process_cls.__name__ != expected_class_name:
        issues.append(
            f"Class name '{process_cls.__name__}' should be '{expected_class_name}' derived from '{func.__name__}'."
        )

    matched_process_params: set[str] = set()
    for func_name, (func_ann, func_default) in func_params.items():
        expected_name = func_name
        expected_ann = func_ann

        # Special handling for CoordCombinerProtocol -> CoordCombinerModel mapping
        if _is_optional_coord_combiner_protocol(func_ann):
            expected_name = f"{func_name}_model"
            expected_ann = CoordCombinerModel | None
        elif _is_coord_combiner_protocol(func_ann):
            expected_name = f"{func_name}_model"
            expected_ann = CoordCombinerModel

        if expected_name not in process_params:
            issues.append(
                f"Missing process parameter '{expected_name}' mapped from function parameter '{func_name}'."
            )
            continue

        process_ann, process_default = process_params[expected_name]
        matched_process_params.add(expected_name)

        if not _types_match(expected_ann, process_ann):
            issues.append(
                f"Type mismatch for '{expected_name}': function expects {_annotation_str(expected_ann)}, "
                f"process defines {_annotation_str(process_ann)}."
            )

        defaults_match = (
            func_default is inspect._empty
            and process_default is inspect._empty
            or func_default == process_default
        )
        if not defaults_match:
            issues.append(
                f"Default mismatch for '{expected_name}': function has {func_default!r}, process has {process_default!r}."
            )

    extra_process_params = set(process_params) - matched_process_params
    for name in sorted(extra_process_params):
        issues.append(f"Process parameter '{name}' has no counterpart in the function.")

    return issues
