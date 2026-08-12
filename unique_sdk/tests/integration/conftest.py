"""
SDK setup for live integration tests under ``tests/integration``.

Loads credentials from ``.env.qa`` in this directory (see ``.env.qa.example``)
and configures ``unique_sdk`` the same way as unique-cli.

Each test can write inspectable JSON under ``artifacts/<test>/<run_id>/``
via the ``integration_artifacts`` fixture. Artifact run directories are gitignored
and pruned (older than 2 days, max 20 per test).
"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from dotenv import dotenv_values

import unique_sdk
from unique_sdk.api_resources._space import Space

_ENV_FILE = Path(__file__).parent / ".env.qa"
_ARTIFACTS_ROOT = Path(__file__).parent / "artifacts"
_ARTIFACT_MAX_AGE = timedelta(days=2)
_ARTIFACT_MAX_PER_TEST = 20


@dataclass(frozen=True)
class QaIntegrationConfig:
    """Credentials and options for QA integration tests."""

    api_key: str
    app_id: str
    user_id: str
    company_id: str
    api_base: str
    assistant_id: str | None = None
    scope_id: str | None = None

    def __repr__(self) -> str:
        """Omit secrets when pytest prints fixture values on failure."""
        return (
            "QaIntegrationConfig("
            f"api_key='***', app_id={self.app_id!r}, user_id={self.user_id!r}, "
            f"company_id={self.company_id!r}, api_base={self.api_base!r}, "
            f"assistant_id={self.assistant_id!r}, scope_id={self.scope_id!r})"
        )

    @classmethod
    def from_env(cls, env_vars: dict[str, str | None]) -> QaIntegrationConfig:
        def require(name: str) -> str:
            value = (env_vars.get(name) or "").strip()
            if not value:
                raise ValueError(f"{name} is required")
            return value

        def optional(name: str) -> str | None:
            value = (env_vars.get(name) or "").strip()
            return value or None

        return cls(
            api_key=require("UNIQUE_API_KEY"),
            app_id=require("UNIQUE_APP_ID"),
            user_id=require("UNIQUE_USER_ID"),
            company_id=require("UNIQUE_COMPANY_ID"),
            api_base=require("UNIQUE_API_BASE").strip("'\""),
            assistant_id=optional("UNIQUE_ASSISTANT_ID"),
            scope_id=optional("UNIQUE_SCOPE_ID"),
        )


class IntegrationArtifacts:
    """Writes JSON artifacts for a single integration test run."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def write(self, name: str, payload: Any) -> Path:
        """Serialize ``payload`` to ``{name}.json`` and return the path."""
        path = self.directory / f"{name}.json"
        path.write_text(
            json.dumps(payload, indent=2, default=str, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def write_text(self, name: str, text: str, *, suffix: str = ".txt") -> Path:
        """Write plain text (e.g. the assistant answer) for easy manual inspection."""
        filename = name if name.endswith(suffix) else f"{name}{suffix}"
        path = self.directory / filename
        path.write_text(text, encoding="utf-8")
        return path


def _safe_test_dirname(nodeid: str) -> str:
    """Turn a pytest nodeid into a filesystem-safe directory name."""
    name = nodeid.split("::")[-1]
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def prune_artifact_runs(
    test_dir: Path,
    *,
    max_age: timedelta = _ARTIFACT_MAX_AGE,
    max_keep: int = _ARTIFACT_MAX_PER_TEST,
    now: datetime | None = None,
) -> list[Path]:
    """
    Prune run directories under ``test_dir``.

    Deletes runs older than ``max_age``, then keeps only the newest ``max_keep``
    remaining runs (by directory name / run id). Returns removed paths.
    """
    if not test_dir.is_dir():
        return []

    current = now or datetime.now(UTC)
    removed: list[Path] = []
    retained: list[Path] = []

    for run_dir in test_dir.iterdir():
        if not run_dir.is_dir():
            continue
        mtime = datetime.fromtimestamp(run_dir.stat().st_mtime, tz=UTC)
        if current - mtime > max_age:
            shutil.rmtree(run_dir, ignore_errors=True)
            removed.append(run_dir)
        else:
            retained.append(run_dir)

    # Run ids are UTC timestamps (sortable); newest first.
    retained.sort(key=lambda path: path.name, reverse=True)
    for run_dir in retained[max_keep:]:
        shutil.rmtree(run_dir, ignore_errors=True)
        removed.append(run_dir)

    return removed


def _prepare_artifact_run_dir(test_dirname: str, run_id: str) -> Path:
    """Prune old runs for ``test_dirname``, then return a fresh run directory path."""
    test_dir = _ARTIFACTS_ROOT / test_dirname
    test_dir.mkdir(parents=True, exist_ok=True)
    prune_artifact_runs(test_dir)
    return test_dir / run_id


@pytest.fixture(scope="session")
def qa_config() -> QaIntegrationConfig:
    """Load QA credentials from ``tests/integration/.env.qa``."""
    if not _ENV_FILE.exists():
        pytest.skip(
            f"QA env file not found at {_ENV_FILE}. "
            "Copy .env.qa.example to .env.qa and fill in credentials."
        )

    try:
        return QaIntegrationConfig.from_env(dict(dotenv_values(_ENV_FILE)))
    except ValueError as exc:
        pytest.skip(f"QA integration configuration missing: {exc}")


@pytest.fixture(scope="session", autouse=True)
def setup_unique_sdk(qa_config: QaIntegrationConfig) -> None:
    """Configure unique_sdk globals from ``.env.qa`` (same pattern as unique-cli)."""
    unique_sdk.api_key = qa_config.api_key
    unique_sdk.app_id = qa_config.app_id
    unique_sdk.api_base = qa_config.api_base


@pytest.fixture(scope="module")
def space_assistant_id(
    qa_config: QaIntegrationConfig,
) -> Generator[str, None, None]:
    """
    Resolve an assistant ID for message create tests.

    Prefers ``UNIQUE_ASSISTANT_ID`` when set; otherwise creates a temporary
    UniqueAI space and deletes it after the module finishes.
    """
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    fixture_artifacts = IntegrationArtifacts(
        _prepare_artifact_run_dir("_fixtures/space_assistant_id", run_id)
    )

    if qa_config.assistant_id:
        fixture_artifacts.write(
            "resolved_assistant",
            {"source": "UNIQUE_ASSISTANT_ID", "assistantId": qa_config.assistant_id},
        )
        yield qa_config.assistant_id
        return

    space_name = f"sdk-integration-create-message-{uuid.uuid4().hex[:8]}"
    create_space_params: Space.CreateSpaceParams = {
        "name": space_name,
        "fallbackModule": "UniqueAi",
        "modules": [{"name": "UniqueAi", "weight": 10000}],
        "chatUpload": "ENABLED",
    }
    fixture_artifacts.write("create_space_request", dict(create_space_params))

    space: Space | None = None
    try:
        space = Space.create_space(
            user_id=qa_config.user_id,
            company_id=qa_config.company_id,
            **create_space_params,
        )
    except BaseException as exc:
        fixture_artifacts.write(
            "create_space_error",
            {"type": type(exc).__name__, "message": str(exc)},
        )
        raise
    finally:
        if space is not None:
            fixture_artifacts.write("create_space_response", space)

    assert space is not None
    space_id = space["id"]
    fixture_artifacts.write(
        "resolved_assistant",
        {"source": "created", "assistantId": space_id, "name": space_name},
    )
    try:
        yield space_id
    finally:
        try:
            Space.delete_space(
                user_id=qa_config.user_id,
                company_id=qa_config.company_id,
                space_id=space_id,
            )
        except Exception:
            pass


@pytest.fixture
def integration_artifacts(
    request: pytest.FixtureRequest,
    qa_config: QaIntegrationConfig,
) -> IntegrationArtifacts:
    """
    Per-test artifact directory under ``tests/integration/artifacts/``.

    Layout: ``artifacts/<test_name>/<utc_timestamp>/``
    Always writes ``meta.json`` (no secrets) so a run is easy to find.
    Prunes runs older than 2 days and keeps at most 20 per test.
    """
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    directory = _prepare_artifact_run_dir(
        _safe_test_dirname(request.node.nodeid),
        run_id,
    )
    artifacts = IntegrationArtifacts(directory)
    artifacts.write(
        "meta",
        {
            "test": request.node.nodeid,
            "runId": run_id,
            "apiBase": qa_config.api_base,
            "assistantId": qa_config.assistant_id,
            "scopeId": qa_config.scope_id,
            "artifactDir": str(directory),
            "retention": {
                "maxAgeDays": _ARTIFACT_MAX_AGE.days,
                "maxPerTest": _ARTIFACT_MAX_PER_TEST,
            },
        },
    )
    # Print so the path is visible in pytest output without opening the tree.
    print(f"\nintegration artifacts: {directory}")
    return artifacts
