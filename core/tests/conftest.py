"""Pytest bootstrap for core tests."""

import os

# Core imports build SQLAlchemy engines at import time, so test collection
# needs a dummy database URL even for tests that never open a real connection.
os.environ.setdefault("DATABASE_URL", "postgresql://dummy:dummy@localhost/dummy")
os.environ.setdefault("ENVIRONMENT", "development")
