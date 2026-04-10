"""Load git-tracked shared test parameters."""

from typing import Any

from inspectui.core.tests.test_params import TEST_PARAMS


def load_shared_test_params() -> dict[str, dict[str, Any]]:
    """Load shared test parameters from repository config.

    Returns:
        Map of test name -> parameter dictionary.
    """
    return {k: v.copy() for k, v in TEST_PARAMS.items()}


def get_shared_test_params(*, test_name: str) -> dict[str, Any]:
    """Get shared params for one test.

    Args:
        test_name: Registered test name.

    Returns:
        Parameters for that test, if present.
    """
    params = TEST_PARAMS.get(test_name, {})
    if isinstance(params, dict):
        return params.copy()
    return {}
