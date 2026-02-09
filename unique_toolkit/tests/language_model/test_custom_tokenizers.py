import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from unique_toolkit.language_model.infos import _load_custom_encoder


@pytest.mark.ai
class TestLoadCustomEncoder:
    def test_raises_when_env_var_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="UNIQUE_CUSTOM_TOKENIZERS_PATH"):
                _load_custom_encoder("my_tokenizer")

    def test_raises_when_tokenizer_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"UNIQUE_CUSTOM_TOKENIZERS_PATH": tmpdir}):
                with pytest.raises(
                    FileNotFoundError, match="Custom tokenizer not found"
                ):
                    _load_custom_encoder("nonexistent")

    def test_loads_valid_tokenizer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bundled_qwen = (
                Path(__file__).parent.parent.parent
                / "unique_toolkit"
                / "_common"
                / "token"
                / "tokenizers"
                / "qwen"
                / "tokenizer.json"
            )

            custom_dir = Path(tmpdir) / "my_custom_tokenizer"
            custom_dir.mkdir()
            shutil.copy(bundled_qwen, custom_dir / "tokenizer.json")

            with patch.dict(os.environ, {"UNIQUE_CUSTOM_TOKENIZERS_PATH": tmpdir}):
                encode = _load_custom_encoder("my_custom_tokenizer")

                assert callable(encode)
                result = encode("Hello")
                assert isinstance(result, list)
                assert all(isinstance(x, int) for x in result)
