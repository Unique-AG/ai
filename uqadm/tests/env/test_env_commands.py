"""Tests for uqadm env subcommands (create, list, show, set-default, delete)."""

from __future__ import annotations

from pathlib import Path

import pytest

from uqadm.env.create import cmd_env_create
from uqadm.env.delete import cmd_env_delete
from uqadm.env.list import cmd_env_list
from uqadm.env.set_default import cmd_env_set_default
from uqadm.env.show import cmd_env_show

# helpers


def _make_slot(
    envs_dir: Path, slot: str, user_id: str = "u1", company_id: str = "c1"
) -> Path:
    path = envs_dir / f".{slot}.env"
    path.write_text(
        f"UNIQUE_USER_ID={user_id}\nUNIQUE_COMPANY_ID={company_id}\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


# --- env create ---


def test_create_writes_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    cmd_env_create(
        "qa",
        force=False,
        set_default=False,
        non_interactive=True,
        user_id="user_qa",
        company_id="co_qa",
        api_key=None,
        app_id=None,
        api_base=None,
    )
    env_file = tmp_path / "envs" / ".qa.env"
    assert env_file.is_file()
    content = env_file.read_text()
    assert "UNIQUE_USER_ID=user_qa" in content
    assert "UNIQUE_COMPANY_ID=co_qa" in content


def test_create_refuses_to_overwrite_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    envs = tmp_path / "envs"
    envs.mkdir(parents=True, exist_ok=True)
    _make_slot(envs, "qa")

    import typer

    with pytest.raises(typer.Exit):
        cmd_env_create(
            "qa",
            force=False,
            set_default=False,
            non_interactive=True,
            user_id="u2",
            company_id="c2",
            api_key=None,
            app_id=None,
            api_base=None,
        )


def test_create_with_force_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    envs = tmp_path / "envs"
    envs.mkdir(parents=True, exist_ok=True)
    _make_slot(envs, "qa", user_id="old")

    cmd_env_create(
        "qa",
        force=True,
        set_default=False,
        non_interactive=True,
        user_id="new",
        company_id="c1",
        api_key=None,
        app_id=None,
        api_base=None,
    )
    content = (envs / ".qa.env").read_text()
    assert "UNIQUE_USER_ID=new" in content


def test_create_set_default_writes_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    cmd_env_create(
        "prod",
        force=False,
        set_default=True,
        non_interactive=True,
        user_id="u",
        company_id="c",
        api_key=None,
        app_id=None,
        api_base=None,
    )
    from uqadm.core.config_file import get_default_slot

    assert get_default_slot() == "prod"


# --- env list ---


def test_list_shows_slots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    envs = tmp_path / "envs"
    envs.mkdir()
    _make_slot(envs, "qa")
    _make_slot(envs, "prod")
    cmd_env_list()
    out = capsys.readouterr().out
    assert "qa" in out
    assert "prod" in out


def test_list_marks_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    envs = tmp_path / "envs"
    envs.mkdir()
    _make_slot(envs, "qa")
    from uqadm.core.config_file import set_default_slot

    set_default_slot("qa")
    cmd_env_list()
    out = capsys.readouterr().out
    assert "qa *" in out or "qa  *" in out or ("qa" in out and "*" in out)


def test_list_empty_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    cmd_env_list()
    out = capsys.readouterr().out
    assert "No slots found" in out


# --- env set-default ---


def test_set_default_accepts_existing_slot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    envs = tmp_path / "envs"
    envs.mkdir()
    _make_slot(envs, "qa")
    cmd_env_set_default("qa")
    from uqadm.core.config_file import get_default_slot

    assert get_default_slot() == "qa"


def test_set_default_rejects_missing_slot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    import typer

    with pytest.raises(typer.Exit):
        cmd_env_set_default("nonexistent")


# --- env show ---


def test_show_prints_resolved_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    monkeypatch.delenv("UQADM_AUTH_FROM_ENV", raising=False)
    envs = tmp_path / "envs"
    envs.mkdir()
    _make_slot(envs, "qa", user_id="user_qa", company_id="co_qa")
    cmd_env_show("qa", cwd=None)
    out = capsys.readouterr().out
    assert "user_qa" in out
    assert "co_qa" in out


# --- env delete ---


def test_delete_removes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    envs = tmp_path / "envs"
    envs.mkdir()
    env_file = _make_slot(envs, "qa")
    cmd_env_delete("qa", yes=True)
    assert not env_file.exists()


def test_delete_clears_default_when_deleted_slot_was_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    envs = tmp_path / "envs"
    envs.mkdir()
    _make_slot(envs, "qa")
    from uqadm.core.config_file import get_default_slot, set_default_slot

    set_default_slot("qa")
    cmd_env_delete("qa", yes=True)
    assert get_default_slot() is None


def test_delete_rejects_missing_slot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    import typer

    with pytest.raises(typer.Exit):
        cmd_env_delete("ghost", yes=True)
