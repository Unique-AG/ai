import os
from functools import lru_cache
from pathlib import Path

import tiktoken
from litellm.utils import token_counter
from tokenizers import Tokenizer

from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

DEFAULT_ENCODING = os.getenv("UNIQUE_DEFAULT_TOKENIZER_ENCODING", "cl100k_base")

CUSTOM_TOKENIZER_MODELS: dict[LanguageModelName, Path] = {
    LanguageModelName.LITELLM_QWEN_3: Path("tokenizers/qwen/tokenizer.json"),
    LanguageModelName.LITELLM_QWEN_3_THINKING: Path("tokenizers/qwen/tokenizer.json"),
    LanguageModelName.LITELLM_DEEPSEEK_R1: Path("tokenizers/deepseek/tokenizer.json"),
    LanguageModelName.LITELLM_DEEPSEEK_V3: Path("tokenizers/deepseek/tokenizer.json"),
}


@lru_cache(maxsize=10)
def _load_tokenizer(tokenizer_path: Path) -> Tokenizer:
    full_path = Path(__file__).parent / tokenizer_path
    if not full_path.exists():
        raise FileNotFoundError(
            f"Tokenizer file not found: {full_path}. "
            "Ensure tokenizer files are bundled in the package."
        )
    return Tokenizer.from_file(str(full_path))


def _get_custom_tokenizer(model_name: LanguageModelName) -> dict | None:
    if model_name not in CUSTOM_TOKENIZER_MODELS:
        return None

    tokenizer_path = CUSTOM_TOKENIZER_MODELS[model_name]
    tokenizer = _load_tokenizer(tokenizer_path)

    return {
        "type": "huggingface_tokenizer",
        "tokenizer": tokenizer,
    }


def count_tokens_for_model(
    text: str,
    model: LanguageModelInfo | LanguageModelName | None = None,
) -> int:
    """Count tokens using the appropriate tokenizer for the model.

    Args:
        text: The text to count tokens for.
        model: Either a LanguageModelInfo, LanguageModelName, or None.
            If None, falls back to tiktoken with DEFAULT_ENCODING
            (configurable via UNIQUE_DEFAULT_TOKENIZER_ENCODING env var).

    Returns:
        The number of tokens in the text.
    """
    if not text:
        return 0

    # Fallback to tiktoken if no model provided
    if model is None:
        encoder = tiktoken.get_encoding(DEFAULT_ENCODING)
        return len(encoder.encode(text))

    if isinstance(model, LanguageModelName):
        model_info = LanguageModelInfo.from_name(model)
    else:
        model_info = model

    model_name = model_info.name

    litellm_model_name = model_name
    custom_tokenizer = None
    if isinstance(model_name, LanguageModelName):
        litellm_model_name = model_name.get_litellm_name()
        custom_tokenizer = _get_custom_tokenizer(model_name)

    if custom_tokenizer:
        return token_counter(
            model=litellm_model_name,
            text=text,
            custom_tokenizer=custom_tokenizer,
        )
    return token_counter(
        model=litellm_model_name,
        text=text,
    )
