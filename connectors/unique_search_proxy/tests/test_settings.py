from pathlib import Path

import pytest

from unique_search_proxy.web.settings import get_env_path


class TestGetEnvPath:
    @pytest.mark.ai
    def test_returns_path(self):
        """
        Purpose: Verify get_env_path returns a Path pointing to .env.
        Why this matters: Incorrect env path prevents loading environment variables.
        Setup summary: Call get_env_path and assert type and filename.
        """
        result = get_env_path()
        assert isinstance(result, Path)
        assert result.name == ".env"
