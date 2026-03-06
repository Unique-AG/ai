from pathlib import Path

from settings import get_env_path


class TestGetEnvPath:
    def test_returns_path(self):
        result = get_env_path()
        assert isinstance(result, Path)
        assert result.name == ".env"
