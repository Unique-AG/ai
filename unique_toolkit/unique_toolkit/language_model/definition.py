import warnings
from datetime import date
from enum import StrEnum
from typing import ClassVar, Optional, Type, TypeVar

from pydantic import BaseModel

from unique_toolkit.language_model.schemas import (
    LanguageModelName,
)

T = TypeVar("T", bound="LanguageModelName")


class LanguageModelProvider(StrEnum):
    AZURE = "AZURE"

class TokenLimits(BaseModel):
    token_limit: Optional[int] = None
    token_limit_input: Optional[int] = None
    token_limit_output: Optional[int] = None

class LanguageModelInfo(BaseModel):
    name: LanguageModelName
    provider: LanguageModelProvider
    
    token_limits: TokenLimits = TokenLimits()

    info_cutoff_at: date
    published_at: date
    retirement_at: Optional[date] = None

    deprecated: bool = False
    deprecated_text: Optional[str] = None


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
    def token_limits(self) -> TokenLimits:
        return self.info.token_limits

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
    info_cutoff_at: date,
    published_at: date,
    token_limit: Optional[int] = None,
    token_limit_input: Optional[int] = None,
    token_limit_output: Optional[int] = None,
    retirement_at: Optional[date] = None,
    deprecated: bool = False,
    deprecated_text: str = "",
) -> Type[LanguageModel]:
    info = LanguageModelInfo(
        name=model_name,
        provider=provider,
        token_limits=TokenLimits(
            token_limit=token_limit,
            token_limit_input=token_limit_input,
            token_limit_output=token_limit_output,
        ),
        info_cutoff_at=info_cutoff_at,
        published_at=published_at,
        retirement_at=retirement_at,
        deprecated=deprecated,
        deprecated_text=deprecated_text,
    )

    class Model(LanguageModel):
        _info = info

    return Model
