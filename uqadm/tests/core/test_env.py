"""Tests for per-slot env file resolution (including UQADM_HOME lookup)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner
from unique_sdk.cli.config import load_config

from uqadm.cli import app
from uqadm.core.env import MissingSlotEnvFileError, env_file_for_slot


def test_env_file_prefers_hidden_over_visible(tmp_path: Path) -> None:
    hidden = tmp_path / ".qa.env"
    visible = tmp_path / "qa.env"
    hidden.write_text("UNIQUE_USER_ID=u1\n", encoding="utf-8")
    visible.write_text("UNIQUE_USER_ID=u2\n", encoding="utf-8")
    assert env_file_for_slot("qa", cwd=tmp_path) == hidden


def test_env_file_falls_back_to_visible(tmp_path: Path) -> None:
    visible = tmp_path / "prod.env"
    visible.write_text("UNIQUE_USER_ID=u1\n", encoding="utf-8")
    assert env_file_for_slot("prod", cwd=tmp_path) == visible


def test_env_file_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(MissingSlotEnvFileError) as exc_info:
        env_file_for_slot("prod", cwd=tmp_path)
    msg = str(exc_info.value)
    assert ".prod.env" in msg
    assert "prod.env" in msg
    assert "Searched in" in msg
    assert "UNIQUE_USER_ID" in msg
    assert "unique_auth_user_id" in msg


def test_missing_slot_env_is_file_not_found_subclass(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        env_file_for_slot("x", cwd=tmp_path)


def test_env_file_found_in_uqadm_home_envs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Slot resolved from UQADM_HOME/envs/ when cwd doesn't contain it."""
    envs = tmp_path / "envs"
    envs.mkdir()
    (envs / ".myslot.env").write_text("UNIQUE_USER_ID=x\n", encoding="utf-8")
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    # Passing a cwd that does NOT have the file; envs_dir() should be tried next.
    other = tmp_path / "other"
    other.mkdir()
    assert env_file_for_slot("myslot", cwd=other) == envs / ".myslot.env"


def test_env_file_cwd_wins_over_uqadm_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    envs = tmp_path / "envs"
    envs.mkdir()
    (envs / ".slot.env").write_text("UNIQUE_USER_ID=from_home\n", encoding="utf-8")
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))

    explicit_cwd = tmp_path / "explicit"
    explicit_cwd.mkdir()
    (explicit_cwd / ".slot.env").write_text(
        "UNIQUE_USER_ID=from_cwd\n", encoding="utf-8"
    )

    result = env_file_for_slot("slot", cwd=explicit_cwd)
    assert result == explicit_cwd / ".slot.env"


def test_cli_missing_env_file_exits_2_with_instructions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    # click/Typer <8.2 defaults mix_stderr=True; pass mix_stderr=False for a
    # separate stderr stream. Newer versions removed the kwarg (stderr separate).
    try:
        runner = CliRunner(mix_stderr=False)  # type: ignore[call-arg]
    except TypeError:
        runner = CliRunner()
    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "space", "list", "--slot", "missing_slot"],
    )
    assert result.exit_code != 0
    try:
        out = (result.stdout or "") + (result.stderr or "")
    except ValueError:
        out = result.output or ""
    assert "no credentials file" in out
    assert "Searched in" in out
    assert ".missing_slot.env" in out
    assert "missing_slot.env" in out
    assert "UNIQUE_USER_ID" in out
    assert "unique_auth_user_id" in out


def test_env_file_hidden_only(tmp_path: Path) -> None:
    hidden = tmp_path / ".1.env"
    hidden.write_text("UNIQUE_USER_ID=x\n", encoding="utf-8")
    assert env_file_for_slot("1", cwd=tmp_path) == hidden


def test_env_file_visible_case_sensitive_suffix(tmp_path: Path) -> None:
    """Only ``.env`` suffix is used; ``slot`` is the stem before ``.env``."""
    f = tmp_path / "MySlot.env"
    f.write_text("UNIQUE_USER_ID=x\n", encoding="utf-8")
    assert env_file_for_slot("MySlot", cwd=tmp_path) == f


@pytest.fixture
def restore_env():
    keys = (
        "UNIQUE_USER_ID",
        "UNIQUE_COMPANY_ID",
        "UNIQUE_API_KEY",
        "UNIQUE_APP_ID",
        "UNIQUE_API_BASE",
        "unique_auth_user_id",
        "unique_auth_company_id",
        "UNIQUE_AUTH_USER_ID",
        "UNIQUE_AUTH_COMPANY_ID",
        "unique_app_id",
        "unique_app_key",
        "UNIQUE_APP_KEY",
        "unique_api_base_url",
        "UNIQUE_API_BASE_URL",
    )
    before = {k: os.environ.get(k) for k in keys}
    yield
    for k in keys:
        v = before.get(k)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_load_slot_reads_visible_file(tmp_path: Path, restore_env) -> None:
    from uqadm.core.env import load_slot

    env_path = tmp_path / "slotb.env"
    env_path.write_text(
        "UNIQUE_USER_ID=user_visible\n"
        "UNIQUE_COMPANY_ID=co_visible\n"
        "UNIQUE_API_BASE=https://example.test\n",
        encoding="utf-8",
    )
    loaded = load_slot("slotb", cwd=tmp_path)
    assert loaded == env_path
    assert os.environ["UNIQUE_USER_ID"] == "user_visible"
    assert os.environ["UNIQUE_COMPANY_ID"] == "co_visible"


def test_load_slot_toolkit_auth_names_populate_unique_keys(
    tmp_path: Path, restore_env
) -> None:
    from uqadm.core.env import load_slot

    env_path = tmp_path / "tk.env"
    env_path.write_text(
        "unique_auth_user_id=user_from_toolkit\n"
        "unique_auth_company_id=company_from_toolkit\n"
        "UNIQUE_API_BASE=https://example.test\n",
        encoding="utf-8",
    )
    load_slot("tk", cwd=tmp_path)
    assert os.environ["UNIQUE_USER_ID"] == "user_from_toolkit"
    assert os.environ["UNIQUE_COMPANY_ID"] == "company_from_toolkit"
    cfg = load_config()
    assert cfg.user_id == "user_from_toolkit"
    assert cfg.company_id == "company_from_toolkit"


def test_load_slot_unique_auth_uppercase_aliases(tmp_path: Path, restore_env) -> None:
    from uqadm.core.env import load_slot

    env_path = tmp_path / "up.env"
    env_path.write_text(
        "UNIQUE_AUTH_USER_ID=user_upper_alias\nUNIQUE_AUTH_COMPANY_ID=co_upper_alias\n",
        encoding="utf-8",
    )
    load_slot("up", cwd=tmp_path)
    assert os.environ["UNIQUE_USER_ID"] == "user_upper_alias"
    assert os.environ["UNIQUE_COMPANY_ID"] == "co_upper_alias"


def test_load_slot_unique_user_id_wins_over_toolkit_alias(
    tmp_path: Path, restore_env
) -> None:
    from uqadm.core.env import load_slot

    env_path = tmp_path / "win.env"
    env_path.write_text(
        "UNIQUE_USER_ID=user_sdk\n"
        "unique_auth_user_id=user_toolkit\n"
        "UNIQUE_COMPANY_ID=co_sdk\n"
        "unique_auth_company_id=co_toolkit\n",
        encoding="utf-8",
    )
    load_slot("win", cwd=tmp_path)
    assert os.environ["UNIQUE_USER_ID"] == "user_sdk"
    assert os.environ["UNIQUE_COMPANY_ID"] == "co_sdk"


def test_load_slot_toolkit_app_and_api_aliases(tmp_path: Path, restore_env) -> None:
    from uqadm.core.env import load_slot

    env_path = tmp_path / "appapi.env"
    env_path.write_text(
        "UNIQUE_USER_ID=u1\n"
        "UNIQUE_COMPANY_ID=c1\n"
        "unique_app_key=ukey_from_app\n"
        "unique_app_id=app_from_app\n"
        "unique_api_base_url=https://gw.example/public/chat-gen2\n",
        encoding="utf-8",
    )
    load_slot("appapi", cwd=tmp_path)
    assert os.environ["UNIQUE_API_KEY"] == "ukey_from_app"
    assert os.environ["UNIQUE_APP_ID"] == "app_from_app"
    assert os.environ["UNIQUE_API_BASE"] == "https://gw.example/public/chat-gen2"


def test_load_slot_unique_api_key_wins_over_unique_app_key(
    tmp_path: Path, restore_env
) -> None:
    from uqadm.core.env import load_slot

    env_path = tmp_path / "keywin.env"
    env_path.write_text(
        "UNIQUE_USER_ID=u1\n"
        "UNIQUE_COMPANY_ID=c1\n"
        "UNIQUE_API_KEY=ukey_sdk\n"
        "unique_app_key=ukey_toolkit\n",
        encoding="utf-8",
    )
    load_slot("keywin", cwd=tmp_path)
    assert os.environ["UNIQUE_API_KEY"] == "ukey_sdk"


def test_load_slot_unique_api_base_url_uppercase_alias(
    tmp_path: Path, restore_env
) -> None:
    from uqadm.core.env import load_slot

    env_path = tmp_path / "burl.env"
    env_path.write_text(
        "UNIQUE_USER_ID=u1\n"
        "UNIQUE_COMPANY_ID=c1\n"
        "UNIQUE_API_BASE_URL=https://upper.example\n",
        encoding="utf-8",
    )
    load_slot("burl", cwd=tmp_path)
    assert os.environ["UNIQUE_API_BASE"] == "https://upper.example/public/chat"


def test_load_slot_unique_api_base_url_with_path_passes_through_unchanged(
    tmp_path: Path, restore_env
) -> None:
    from uqadm.core.env import load_slot

    env_path = tmp_path / "pub.env"
    env_path.write_text(
        "UNIQUE_USER_ID=u1\n"
        "UNIQUE_COMPANY_ID=c1\n"
        "unique_api_base_url=http://localhost:8092/public\n",
        encoding="utf-8",
    )
    load_slot("pub", cwd=tmp_path)
    assert os.environ["UNIQUE_API_BASE"] == "http://localhost:8092/public"
