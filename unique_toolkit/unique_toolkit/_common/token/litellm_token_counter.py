from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import litellm
from tokenizers import Tokenizer
import tiktoken


if TYPE_CHECKING:
    from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

TOKENIZERS_DIR = Path(__file__).parent / "tokenizers"

CUSTOM_TOKENIZER_MODELS = {
    "LITELLM_QWEN_3": "qwen/tokenizer.json",
    "LITELLM_QWEN_3_THINKING": "qwen/tokenizer.json",
    "LITELLM_DEEPSEEK_R1": "deepseek/tokenizer.json",
    "LITELLM_DEEPSEEK_V3": "deepseek/tokenizer.json",
}


@lru_cache(maxsize=10)
def _load_tokenizer(tokenizer_path: str) -> Tokenizer:
    full_path = TOKENIZERS_DIR / tokenizer_path
    if not full_path.exists():
        raise FileNotFoundError(
            f"Tokenizer file not found: {full_path}. "
            "Ensure tokenizer files are bundled in the package."
        )
    return Tokenizer.from_file(str(full_path))


def _get_custom_tokenizer(model_name: "LanguageModelName") -> dict | None:
    if model_name.name not in CUSTOM_TOKENIZER_MODELS:
        return None
    
    tokenizer_path = CUSTOM_TOKENIZER_MODELS[model_name.name]
    tokenizer = _load_tokenizer(tokenizer_path)
    
    return {
        "type": "huggingface_tokenizer",
        "tokenizer": tokenizer,
    }


def count_tokens_for_model(text: str, model_info: "LanguageModelInfo") -> int:
    from unique_toolkit.language_model.infos import get_litellm_name
    
    if not text:
        return 0
    
    model_name = model_info.name
    litellm_model_name = get_litellm_name(model_name)
    custom_tokenizer = _get_custom_tokenizer(model_name)
    
    try:
        if custom_tokenizer:
            return litellm.token_counter(
                model=litellm_model_name,
                text=text,
                custom_tokenizer=custom_tokenizer,
            )
        return litellm.token_counter(
            model=litellm_model_name,
            text=text,
        )
    except Exception:        
        try:
            encoder = tiktoken.get_encoding(model_info.encoder_name)
            return len(encoder.encode(text))
        except Exception:
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
