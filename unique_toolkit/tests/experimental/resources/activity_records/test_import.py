from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = pytest.mark.ai


def test_package_imports_without_activity_records_dependencies() -> None:
    code = """
import importlib.abc
import sys

blocked = {"asyncpg", "prometheus_client"}

class BlockedImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in blocked:
            raise ImportError(f"blocked: {fullname}")
        return None

sys.meta_path.insert(0, BlockedImports())
import unique_toolkit
from unique_toolkit.experimental.resources.activity_records import (
    ActivityActor,
    ActivityCloudEvent,
    ActivityEventData,
    enqueue,
)
from unique_toolkit.experimental.resources.activity_records import *

enqueue(
    ActivityCloudEvent(
        source="test",
        type="activity.test",
        data=ActivityEventData(
            actor=ActivityActor(id="user", type="user"),
            company_id="company",
        ),
    )
)
for module_name in (
    "unique_toolkit.experimental.resources.activity_records.store",
    "unique_toolkit.experimental.resources.activity_records.metrics",
):
    try:
        __import__(module_name)
    except ImportError as error:
        assert "Install it with: uv add 'unique-toolkit[activity-records]'" in str(error)
    else:
        raise AssertionError(f"{module_name} imported without its extra")
print("ok")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "ok"
