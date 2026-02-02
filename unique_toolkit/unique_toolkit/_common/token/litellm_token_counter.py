import os
from functools import lru_cache
from pathlib import Path

import tiktoken
from litellm.utils import token_counter
from tokenizers import Tokenizer

from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

DEFAULT_ENCODING = os.getenv("UNIQUE_DEFAULT_TOKENIZER_ENCODING", "cl100k_base")

CUSTOM_TOKENIZER_MODELS: dict[LanguageModelName, str] = {
    LanguageModelName.LITELLM_QWEN_3: "qwen",
    LanguageModelName.LITELLM_QWEN_3_THINKING: "qwen",
    LanguageModelName.LITELLM_DEEPSEEK_R1: "deepseek",
    LanguageModelName.LITELLM_DEEPSEEK_V3: "deepseek",
}


@lru_cache(maxsize=10)
def _load_tokenizer(tokenizer_name: str) -> Tokenizer:
    full_path = Path(__file__).parent / "tokenizers" / tokenizer_name / "tokenizer.json"
    if not full_path.exists():
        raise FileNotFoundError(
            f"Tokenizer file not found: {full_path}. "
            "Ensure tokenizer files are bundled in the package."
        )
    return Tokenizer.from_file(str(full_path))


def _get_custom_tokenizer(model_name: LanguageModelName) -> dict | None:
    if model_name not in CUSTOM_TOKENIZER_MODELS:
        return None

    tokenizer_name = CUSTOM_TOKENIZER_MODELS[model_name]
    tokenizer = _load_tokenizer(tokenizer_name)

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

    if model is None:
        encoder = tiktoken.get_encoding(DEFAULT_ENCODING)
        return len(encoder.encode(text))

    if isinstance(model, LanguageModelName):
        model_name = model
    elif isinstance(model, LanguageModelInfo):
        model_name = model.name

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
