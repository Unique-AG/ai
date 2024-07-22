import warnings
from datetime import date
from enum import StrEnum
from typing import ClassVar, Type, TypeVar

from pydantic import BaseModel

from unique_toolkit.language_model.schemas import (
    LanguageModelName,
)

T = TypeVar("T", bound="LanguageModelName")


class LanguageModelProvider(StrEnum):
    AZURE = "AZURE"


class LanguageModelInfo(BaseModel):
    name: LanguageModelName
    provider: LanguageModelProvider
    
    token_limit: int
    max_tokens: int
    tokens_per_min: int

    info_cutoff_at: date
    published_at: date
    retirement_at: date

    deprecated: bool = False
    deprecated_text: str = ""


class LanguageModel:
    _info: ClassVar[LanguageModelInfo]

    def __init__(self, model_name: LanguageModelName):
        self._ai_info = self.get_model_info(model_name)

    @property
    def info(self) -> LanguageModelInfo:
        return self._ai_info

    @property
    def name(self) -> LanguageModelName:
        return self.info.name

    @property
    def display_name(self) -> str:
        return self.info.name.name

    @property
    def token_limit(self) -> int:
        return self.info.token_limit

    @classmethod
    def get_model_info(cls, model_name: LanguageModelName) -> LanguageModelInfo:
        for subclass in cls.__subclasses__():
            if hasattr(subclass, "info") and subclass._info.name == model_name:
                if subclass._info.deprecated:
                    warning_text = f"WARNING: {subclass._info.name} is deprecated. {subclass._info.deprecated_text}"
                    print(warning_text)
                    warnings.warn(warning_text, DeprecationWarning, stacklevel=2)
                return subclass._info
        raise ValueError(f"Model {model_name} not found.")

    @classmethod
    def list_models(cls):
        return [
            subclass.info
            for subclass in cls.__subclasses__()
            if hasattr(subclass, "info")
        ]


def create_ai_model_info(
    model_name: LanguageModelName,
    provider: LanguageModelProvider,
    token_limit: int,
    max_tokens: int,
    tokens_per_min: int,
    info_cutoff_at: date,
    published_at: date,
    retirement_at: date,
    deprecated: bool = False,
    deprecated_text: str = "",
) -> Type[LanguageModelName]:
    info = LanguageModelInfo(
        name=model_name,
        provider=provider,
        token_limit=token_limit,
        max_tokens=max_tokens,
        tokens_per_min=tokens_per_min,
        info_cutoff_at=info_cutoff_at,
        published_at=published_at,
        retirement_at=retirement_at,
        deprecated=deprecated,
        deprecated_text=deprecated_text,
    )

    class Model(LanguageModel):
        _info = info

    return Model
