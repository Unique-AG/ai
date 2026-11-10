from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from prometheus_client import CollectorRegistry


class Metrics:
    """Outbox metrics on an isolated registry, with a sample-value helper."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        from prometheus_client import CollectorRegistry as Registry

        from unique_toolkit.experimental.resources.activity_records.metrics import (
            get_or_create_activity_event_outbox_metrics,
        )

        self.registry = registry or Registry()
        self.metrics = get_or_create_activity_event_outbox_metrics(
            registry=self.registry
        )

    def __getattr__(self, name: str) -> object:
        return getattr(self.metrics, name)

    def value(self, name: str, labels: dict[str, str] | None = None) -> float:
        return self.registry.get_sample_value(name, labels) or 0


@contextmanager
def docker_container(
    image: str, container_port: int, *environment: str
) -> Iterator[tuple[str, int]]:
    command = ["docker", "run", "-d", "--rm"]
    for value in environment:
        command.extend(["-e", value])
    command.extend(["-p", f"127.0.0.1::{container_port}", image])
    container = subprocess.run(
        command, capture_output=True, text=True, check=True
    ).stdout.strip()
    try:
        mapping = subprocess.run(
            ["docker", "port", container, f"{container_port}/tcp"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()[0]
        yield container, int(mapping.rsplit(":", 1)[1])
    finally:
        subprocess.run(["docker", "rm", "-f", container], capture_output=True)


async def wait_until(
    connect: Callable[[], Awaitable[Any]], timeout_seconds: float
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            connection = await asyncio.wait_for(connect(), 2)
            await connection.close()
            return
        except Exception as error:
            last_error = error
        await asyncio.sleep(0.5)
    if last_error is not None:
        raise last_error
    raise TimeoutError("service did not become ready")


@pytest.fixture(scope="module")
def docker_tests() -> None:
    if os.getenv("ACTIVITY_RECORDS_DOCKER_TESTS") != "1":
        pytest.skip(
            "Docker tests are disabled; set ACTIVITY_RECORDS_DOCKER_TESTS=1 to enable"
        )
    if shutil.which("docker") is None:
        pytest.skip("Docker is not available: docker CLI was not found")
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        pytest.skip("Docker is not available")
