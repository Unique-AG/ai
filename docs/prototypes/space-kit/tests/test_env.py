from pathlib import Path

import pytest

from space_kit.base import SpaceKitError
from space_kit.env import (
    KitConfig,
    Target,
    load_credentials,
    resolve_env_file,
    target_for_api_base,
)

pytestmark = pytest.mark.ai


@pytest.mark.parametrize(
    ("api_base", "target"),
    [
        ("http://localhost:8092/public", Target.LOCAL),
        ("http://127.0.0.1:8092/public", Target.LOCAL),
        ("https://gateway.qa.example.com/public/chat-gen2", Target.QA),
    ],
)
def test_target_for_api_base_accepts_local_and_qa(
    api_base: str, target: Target
) -> None:
    assert target_for_api_base(api_base=api_base) is target


@pytest.mark.parametrize(
    "api_base",
    [
        "https://gateway.example.com/public/chat-gen2",
        "https://gateway.uat1.example.com/public/chat",
        "https://gateway.qa.other-domain.test/public",
        "https://gateway.qa.example.com.evil.com/public",
    ],
)
def test_target_for_api_base_refuses_every_other_host(api_base: str) -> None:
    with pytest.raises(SpaceKitError, match="refusing API host"):
        _ = target_for_api_base(api_base=api_base)


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "unique.env"
    _ = path.write_text(text, encoding="utf-8")
    return path


def test_load_credentials_reads_harness_eval_key_names(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "export UNIQUE_API_BASE_URL='https://gateway.qa.example.com/public'\n"
        'UNIQUE_APP_KEY="k"\nUNIQUE_APP_ID=a\nUNIQUE_AUTH_USER_ID=u\n'
        "UNIQUE_AUTH_COMPANY_ID=c\n",
    )

    credentials = load_credentials(target=Target.QA, env_file=path)

    assert (credentials.api_key, credentials.user_id) == ("k", "u")


def test_load_credentials_reads_uqadm_key_names(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "UNIQUE_API_BASE=http://localhost:8092/public\n"
        "UNIQUE_USER_ID=u\nUNIQUE_COMPANY_ID=c\n",
    )

    credentials = load_credentials(target=Target.LOCAL, env_file=path)

    assert credentials.api_key == ""
    assert credentials.company_id == "c"


def test_load_credentials_refuses_an_env_file_for_another_target(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path,
        "UNIQUE_API_BASE=http://localhost:8092/public\n"
        "UNIQUE_USER_ID=u\nUNIQUE_COMPANY_ID=c\n",
    )

    with pytest.raises(SpaceKitError, match="points at target local"):
        _ = load_credentials(target=Target.QA, env_file=path)


def test_load_credentials_names_missing_keys_on_qa(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "UNIQUE_API_BASE=https://gateway.qa.example.com/public\n"
        "UNIQUE_USER_ID=u\nUNIQUE_COMPANY_ID=c\n",
    )

    with pytest.raises(SpaceKitError, match="UNIQUE_APP_KEY or UNIQUE_API_KEY"):
        _ = load_credentials(target=Target.QA, env_file=path)


def test_credentials_repr_never_contains_the_key(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "UNIQUE_API_BASE=https://gateway.qa.example.com/public\n"
        "UNIQUE_API_KEY=super-secret\nUNIQUE_APP_ID=a\n"
        "UNIQUE_USER_ID=u\nUNIQUE_COMPANY_ID=c\n",
    )

    credentials = load_credentials(target=Target.QA, env_file=path)

    assert "super-secret" not in repr(credentials)
    assert "super-secret" not in str(credentials)


def test_resolve_env_file_prefers_flag_then_variable_then_config(
    tmp_path: Path,
) -> None:
    config = KitConfig(env_files={Target.QA: tmp_path / "from-config"})
    environ = {"SPACE_KIT_ENV_FILE_QA": str(tmp_path / "from-env")}

    explicit = resolve_env_file(
        target=Target.QA,
        explicit=tmp_path / "flag",
        environ=environ,
        config=config,
    )
    from_env = resolve_env_file(
        target=Target.QA, explicit=None, environ=environ, config=config
    )
    from_config = resolve_env_file(
        target=Target.QA, explicit=None, environ={}, config=config
    )

    assert explicit.name == "flag"
    assert from_env.name == "from-env"
    assert from_config.name == "from-config"


def test_resolve_env_file_explains_how_to_configure(tmp_path: Path) -> None:
    with pytest.raises(SpaceKitError, match="SPACE_KIT_ENV_FILE_LOCAL"):
        _ = resolve_env_file(
            target=Target.LOCAL, explicit=None, environ={}, config=KitConfig()
        )
