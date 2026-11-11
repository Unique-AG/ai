from collections.abc import Callable
from pathlib import Path

import pytest

from space_kit.cli import main
from tests.support.fake_api import API_BASE, FakeSpaceServer

type RunCli = Callable[..., tuple[int, list[str]]]

QA_ENV = f"""
UNIQUE_API_BASE_URL={API_BASE}
UNIQUE_APP_KEY=test-key-not-real
UNIQUE_APP_ID=app_test
UNIQUE_AUTH_USER_ID=user_test
UNIQUE_AUTH_COMPANY_ID=company_test
"""


@pytest.fixture
def server() -> FakeSpaceServer:
    return FakeSpaceServer()


@pytest.fixture
def kit_home(tmp_path: Path) -> Path:
    home = tmp_path / "space-kit"
    home.mkdir()
    env_file = tmp_path / "unique.env.qa"
    _ = env_file.write_text(QA_ENV, encoding="utf-8")
    _ = (home / "envs.yaml").write_text(
        f"env_files:\n  qa: {env_file}\n", encoding="utf-8"
    )
    return home


@pytest.fixture
def run_cli(kit_home: Path, server: FakeSpaceServer) -> RunCli:
    def run(*argv: str, environ: dict[str, str] | None = None) -> tuple[int, list[str]]:
        lines: list[str] = []
        code = main(
            list(argv),
            environ={"SPACE_KIT_HOME": str(kit_home), **(environ or {})},
            transport=server,
            out=lines.append,
        )
        return code, lines

    return run
