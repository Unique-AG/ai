from datetime import date
from enum import StrEnum
from typing import ClassVar, Optional, Type, cast

from pydantic import BaseModel

from unique_toolkit.language_model.schemas import LanguageModelTokenLimits


class LanguageModelName(StrEnum):
    AZURE_GPT_35_TURBO_0613 = "AZURE_GPT_35_TURBO_0613"
    AZURE_GPT_35_TURBO = "AZURE_GPT_35_TURBO"
    AZURE_GPT_35_TURBO_16K = "AZURE_GPT_35_TURBO_16K"
    AZURE_GPT_4_0613 = "AZURE_GPT_4_0613"
    AZURE_GPT_4_TURBO_1106 = "AZURE_GPT_4_TURBO_1106"
    AZURE_GPT_4_VISION_PREVIEW = "AZURE_GPT_4_VISION_PREVIEW"
    AZURE_GPT_4_32K_0613 = "AZURE_GPT_4_32K_0613"
    AZURE_GPT_4_TURBO_2024_0409 = "AZURE_GPT_4_TURBO_2024_0409"
    AZURE_GPT_4o_2024_0513 = "AZURE_GPT_4o_2024_0513"
    AZURE_GPT_4o_MINI_2024_0718 = "AZURE_GPT_4o_MINI_2024_0718"


class LanguageModelProvider(StrEnum):
    AZURE = "AZURE"
    CUSTOM = "CUSTOM"


class LanguageModelInfo(BaseModel):
    name: LanguageModelName | str
    version: str
    provider: LanguageModelProvider

    token_limits: Optional[LanguageModelTokenLimits] = None

    info_cutoff_at: Optional[date] = None
    published_at: Optional[date] = None
    retirement_at: Optional[date] = None

    deprecated_at: Optional[date] = None
    retirement_text: Optional[str] = None


class LanguageModel:
    _info: ClassVar[LanguageModelInfo]

    def __init__(self, model_name: LanguageModelName | str):
        self._model_info = self.get_model_info(model_name)

    @property
    def info(self) -> LanguageModelInfo:
        """
        Returns all infos about the model:
        - name
        - custom_name
        - version
        - provider
        - token_limits
        - info_cutoff_at
        - published_at
        - retirement_at
        - deprecated_at
        - retirement_text
        """
        return self._model_info

    @property
    def name(self) -> LanguageModelName | str:
        """
        Returns the LanguageModelName of the model or the name string when it is a custom / not defined model.
        """
        return self._model_info.name

    @property
    def display_name(self) -> str:
        """
        Returns the name of the model as a string.
        """
        if isinstance(self._model_info.name, LanguageModelName):
            return self._model_info.name.name
        else:
            return self._model_info.name

    @property
    def version(self) -> Optional[str]:
        """
        Returns the version of the model.
        """
        return self._model_info.version

    @property
    def token_limit(self) -> Optional[int]:
        """
        Returns the maximum number of tokens for the model.
        """
        if self._model_info.token_limits:
            return self._model_info.token_limits.token_limit

    @property
    def token_limit_input(self) -> Optional[int]:
        """
        Returns the maximum number of input tokens for the model.
        """
        if self._model_info.token_limits:
            return self._model_info.token_limits.token_limit_input

    @property
    def token_limit_output(self) -> Optional[int]:
        """
        Returns the maximum number of output tokens for the model.
        """
        if self._model_info.token_limits:
            return self._model_info.token_limits.token_limit_output

    @property
    def info_cutoff_at(self) -> Optional[date]:
        """
        Returns the date the model was last updated.
        """
        return self._model_info.info_cutoff_at

    @property
    def published_at(self) -> Optional[date]:
        """
        Returns the date the model was published.
        """
        return self._model_info.published_at

    @property
    def retirement_at(self) -> Optional[date]:
        """
        Returns the date the model will be retired.
        """
        return self._model_info.retirement_at

    @property
    def deprecated_at(self) -> Optional[date]:
        """
        Returns the date the model was deprecated.
        """
        return self._model_info.deprecated_at

    @property
    def retirement_text(self) -> Optional[str]:
        """
        Returns the text that will be displayed when the model is retired.
        """
        return self._model_info.retirement_text

    @property
    def provider(self) -> LanguageModelProvider:
        """
        Returns the provider of the model.
        """
        return self._model_info.provider

    @classmethod
    def get_model_info(cls, model_name: LanguageModelName | str) -> LanguageModelInfo:
        for subclass in cls.__subclasses__():
            if hasattr(subclass, "info") and subclass._info.name == model_name:
                # TODO find alternative solution for warning
                # if subclass._info.retirement_at:
                #     warning_text = f"WARNING: {subclass._info.name} will be retired on {subclass._info.retirement_at.isoformat()} and from then on not accessible anymore. {subclass._info.retirement_text}"
                #     print(warning_text)
                #     warnings.warn(warning_text, DeprecationWarning, stacklevel=2)
                return subclass._info

        return LanguageModelInfo(
            name=model_name,
            version="custom",
            provider=LanguageModelProvider.CUSTOM,
        )

    @classmethod
    def list_models(cls) -> list[LanguageModelInfo]:
        """
        Returns a list of the infos of all available models.
        """

        return [
            cast(LanguageModelInfo, subclass._info)
            for subclass in cls.__subclasses__()
            if hasattr(subclass, "_info")
        ]


def create_language_model(
    name: LanguageModelName,
    version: str,
    provider: LanguageModelProvider,
    info_cutoff_at: date,
    published_at: date,
    token_limit: Optional[int] = None,
    token_limit_input: Optional[int] = None,
    token_limit_output: Optional[int] = None,
    retirement_at: Optional[date] = None,
    deprecated_at: Optional[date] = None,
    retirement_text: Optional[str] = None,
) -> Type[LanguageModel]:
    info = LanguageModelInfo(
        name=name,
        version=version,
        provider=provider,
        token_limits=LanguageModelTokenLimits(
            token_limit=token_limit,
            token_limit_input=token_limit_input,
            token_limit_output=token_limit_output,
        ),
        info_cutoff_at=info_cutoff_at,
        published_at=published_at,
        retirement_at=retirement_at,
        deprecated_at=deprecated_at,
        retirement_text=retirement_text,
    )

    class Model(LanguageModel):
        _info = info

    return Model


############################################################################################################
# Define the models here
############################################################################################################


AzureGpt35Turbo0613 = create_language_model(
    name=LanguageModelName.AZURE_GPT_35_TURBO_0613,
    provider=LanguageModelProvider.AZURE,
    version="0613",
    token_limit=8192,
    info_cutoff_at=date(2021, 9, 1),
    published_at=date(2023, 6, 13),
    retirement_at=date(2024, 10, 1),
)

AzureGpt35Turbo = create_language_model(
    name=LanguageModelName.AZURE_GPT_35_TURBO,
    provider=LanguageModelProvider.AZURE,
    version="0301",
    token_limit=4096,
    info_cutoff_at=date(2021, 9, 1),
    published_at=date(2023, 3, 1),
)


AzureGpt35Turbo16k = create_language_model(
    name=LanguageModelName.AZURE_GPT_35_TURBO_16K,
    provider=LanguageModelProvider.AZURE,
    version="0613",
    token_limit=16382,
    info_cutoff_at=date(2021, 9, 1),
    published_at=date(2023, 6, 13),
    retirement_at=date(2024, 10, 1),
)


AzureGpt40613 = create_language_model(
    name=LanguageModelName.AZURE_GPT_4_0613,
    provider=LanguageModelProvider.AZURE,
    version="0613",
    token_limit=8192,
    info_cutoff_at=date(2021, 9, 1),
    published_at=date(2023, 6, 13),
    deprecated_at=date(2024, 10, 1),
    retirement_at=date(2025, 6, 1),
)


AzureGpt4Turbo1106 = create_language_model(
    name=LanguageModelName.AZURE_GPT_4_TURBO_1106,
    provider=LanguageModelProvider.AZURE,
    version="1106-preview",
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=date(2023, 4, 1),
    published_at=date(2023, 11, 6),
)


AzureGpt4VisionPreview = create_language_model(
    name=LanguageModelName.AZURE_GPT_4_VISION_PREVIEW,
    provider=LanguageModelProvider.AZURE,
    version="vision-preview",
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=date(2023, 4, 1),
    published_at=date(2023, 11, 6),
)

AzureGpt432k0613 = create_language_model(
    name=LanguageModelName.AZURE_GPT_4_32K_0613,
    provider=LanguageModelProvider.AZURE,
    version="1106-preview",
    token_limit=32768,
    info_cutoff_at=date(2021, 9, 1),
    published_at=date(2023, 6, 13),
    deprecated_at=date(2024, 10, 1),
    retirement_at=date(2025, 6, 1),
)

AzureGpt4Turbo20240409 = create_language_model(
    name=LanguageModelName.AZURE_GPT_4_TURBO_2024_0409,
    provider=LanguageModelProvider.AZURE,
    version="turbo-2024-04-09",
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=date(2023, 12, 1),
    published_at=date(2024, 4, 9),
)

AzureGpt4o20240513 = create_language_model(
    name=LanguageModelName.AZURE_GPT_4o_2024_0513,
    provider=LanguageModelProvider.AZURE,
    version="2024-05-13",
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=date(2023, 10, 1),
    published_at=date(2024, 5, 13),
)

AzureGpt4oMini20240718 = create_language_model(
    name=LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
    provider=LanguageModelProvider.AZURE,
    version="2024-07-18",
    token_limit_input=128000,
    token_limit_output=16384,
    info_cutoff_at=date(2023, 10, 1),
    published_at=date(2024, 7, 18),
)
