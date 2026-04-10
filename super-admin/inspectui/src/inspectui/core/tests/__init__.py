"""Test framework: ``BaseTest``, ``TestRegistry``, ``TestRunner``.

Importing this package executes ``builtin`` so decorated tests register on startup.
"""

from inspectui.core.tests.base import BaseTest, TestRegistry
from inspectui.core.tests.runner import TestRunner

__all__ = ["BaseTest", "TestRegistry", "TestRunner"]

from inspectui.core.tests import builtin as _  # noqa: F401
