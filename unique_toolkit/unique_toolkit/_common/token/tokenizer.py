from enum import StrEnum
from pathlib import Path
from typing import Protocol, overload

import tiktoken
from transformers import AutoTokenizer

from unique_toolkit.language_model.infos import EncoderName


class TokenizerType(StrEnum):
    TIKTOKEN = "tiktoken"
    HUGGING_FACE = "hugging_face"


class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]: ...

    def decode(self, tokens: list[int]) -> str: ...


class OpenAITokenizer(Tokenizer):
    def __init__(self, model: str):
        self._encoder = tiktoken.get_encoding(model)

    def encode(self, text: str) -> list[int]:
        return self._encoder.encode(text)

    def decode(self, tokens: list[int]) -> str:
        return self._encoder.decode(tokens)


class HuggingFaceTokenizer(Tokenizer):
    @overload
    def __init__(self, *, model: str): ...

    @overload
    def __init__(self, *, tokenizer_path: Path): ...

    def __init__(self, *, model: str | None = None, tokenizer_path: Path | None = None):
        if model is not None:
            self._encoder = AutoTokenizer.from_pretrained(model)
        elif tokenizer_path is not None:
            self._encoder = AutoTokenizer.from_pretrained(tokenizer_path)
        else:
            raise ValueError("Either model or tokenizer_path must be provided")

    def encode(self, text: str) -> list[int]:
        return self._encoder.encode(text)

    def decode(self, tokens: list[int]) -> str:
        return self._encoder.decode(tokens)


def get_tokenizer(encoder_name: EncoderName | str) -> Tokenizer:
    match encoder_name:
        case EncoderName.O200K_BASE:
            return OpenAITokenizer(model="o200k_base")
        case EncoderName.CL100K_BASE:
            return HuggingFaceTokenizer(model="gpt2")
        case _:
            raise ValueError(f"Encoder name {encoder_name} not supported")
