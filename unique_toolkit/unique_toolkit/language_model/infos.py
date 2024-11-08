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
    AZURE_GPT_4o_2024_0806 = "AZURE_GPT_4o_2024_0806"
    AZURE_GPT_4o_MINI_2024_0718 = "AZURE_GPT_4o_MINI_2024_0718"


class EncoderName(StrEnum):
    O200K_BASE = "o200k_base"
    CL100K_BASE = "cl100k_base"


def get_encoder_name(model_name: LanguageModelName) -> Optional[EncoderName]:
    LMN = LanguageModelName
    match model_name:
        case (
            LMN.AZURE_GPT_35_TURBO
            | LMN.AZURE_GPT_35_TURBO_16K
            | LMN.AZURE_GPT_35_TURBO_0613
        ):
            return EncoderName.CL100K_BASE
        case (
            LMN.AZURE_GPT_4_0613
            | LMN.AZURE_GPT_4_TURBO_1106
            | LMN.AZURE_GPT_4_VISION_PREVIEW
            | LMN.AZURE_GPT_4_32K_0613
            | LMN.AZURE_GPT_4_TURBO_2024_0409
        ):
            return EncoderName.CL100K_BASE
        case (
            LMN.AZURE_GPT_4o_2024_0513
            | LMN.AZURE_GPT_4o_2024_0806
            | LMN.AZURE_GPT_4o_MINI_2024_0718
        ):
            return EncoderName.O200K_BASE
        case _:
            print(f"{model_name} is not supported. Please add encoder information.")
            return None


class LanguageModelProvider(StrEnum):
    AZURE = "AZURE"
    CUSTOM = "CUSTOM"


class LanguageModelInfo(BaseModel):
    name: LanguageModelName | str
    version: str
    provider: LanguageModelProvider

    encoder_name: Optional[EncoderName] = None
    token_limits: Optional[LanguageModelTokenLimits] = None

    info_cutoff_at: Optional[date] = None
    published_at: Optional[date] = None
    retirement_at: Optional[date] = None

    deprecated_at: Optional[date] = None
    retirement_text: Optional[str] = None

    @property
    def display_name(self) -> str:
        """
        Returns the name of the model as a string.
        """
        if isinstance(self.name, LanguageModelName):
            return self.name.name
        else:
            return self.name

    @property
    def token_limit(self) -> Optional[int]:
        """
        Returns the maximum number of tokens for the model.
        """
        if self.token_limits:
            return self.token_limits.token_limit

    @property
    def token_limit_input(self) -> Optional[int]:
        """
        Returns the maximum number of input tokens for the model.
        """
        if self.token_limits:
            return self.token_limits.token_limit_input

    @property
    def token_limit_output(self) -> Optional[int]:
        """
        Returns the maximum number of output tokens for the model.
        """
        if self.token_limits:
            return self.token_limits.token_limit_output


class LanguageModelRegistry:
    models: dict[LanguageModelName, LanguageModelInfo] = {}

    @staticmethod
    def register_language_model(
        name: LanguageModelName,
        version: str,
        provider: LanguageModelProvider,
        info_cutoff_at: date,
        published_at: date,
        encoder_name: Optional[EncoderName] = None,
        token_limit: Optional[int] = None,
        token_limit_input: Optional[int] = None,
        token_limit_output: Optional[int] = None,
        retirement_at: Optional[date] = None,
        deprecated_at: Optional[date] = None,
        retirement_text: Optional[str] = None,
    ) -> LanguageModelInfo:
        info = LanguageModelInfo(
            name=name,
            version=version,
            provider=provider,
            encoder_name=encoder_name,
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
        LanguageModel.models[name] = info

    @staticmethod
    def get_model_info(name: LanguageModelName | str) -> LanguageModelInfo:
        return LanguageModel.models[name]
    
    @staticmethod
    def list_models() -> list[LanguageModelInfo]:
        """
        Returns a list of the infos of all available models.
        """

        return [
            cast(LanguageModelInfo, modelinfo)
            for modelinfo in LanguageModel.models.values()
            if hasattr(modelinfo, "name")
        ]



# Alias to deprecate
LanguageModel = LanguageModelRegistry

############################################################################################################
# Define the models here
############################################################################################################

register_language_model = LanguageModelRegistry.register_language_model

AzureGpt35Turbo0613 = register_language_model(
    name=LanguageModelName.AZURE_GPT_35_TURBO_0613,
    provider=LanguageModelProvider.AZURE,
    version="0613",
    encoder_name=get_encoder_name(LanguageModelName.AZURE_GPT_35_TURBO_0613),
    token_limit=8192,
    info_cutoff_at=date(2021, 9, 1),
    published_at=date(2023, 6, 13),
    retirement_at=date(2024, 10, 1),
)

AzureGpt35Turbo = register_language_model(
    name=LanguageModelName.AZURE_GPT_35_TURBO,
    provider=LanguageModelProvider.AZURE,
    version="0301",
    encoder_name=get_encoder_name(LanguageModelName.AZURE_GPT_35_TURBO),
    token_limit=4096,
    info_cutoff_at=date(2021, 9, 1),
    published_at=date(2023, 3, 1),
)

AzureGpt35Turbo16k = register_language_model(
    name=LanguageModelName.AZURE_GPT_35_TURBO_16K,
    provider=LanguageModelProvider.AZURE,
    version="0613",
    encoder_name=get_encoder_name(LanguageModelName.AZURE_GPT_35_TURBO_16K),
    token_limit=16382,
    info_cutoff_at=date(2021, 9, 1),
    published_at=date(2023, 6, 13),
    retirement_at=date(2024, 10, 1),
)

AzureGpt40613 = register_language_model(
    name=LanguageModelName.AZURE_GPT_4_0613,
    provider=LanguageModelProvider.AZURE,
    version="0613",
    encoder_name=get_encoder_name(LanguageModelName.AZURE_GPT_4_0613),
    token_limit=8192,
    info_cutoff_at=date(2021, 9, 1),
    published_at=date(2023, 6, 13),
    deprecated_at=date(2024, 10, 1),
    retirement_at=date(2025, 6, 1),
)

AzureGpt4Turbo1106 = register_language_model(
    name=LanguageModelName.AZURE_GPT_4_TURBO_1106,
    provider=LanguageModelProvider.AZURE,
    version="1106-preview",
    encoder_name=get_encoder_name(LanguageModelName.AZURE_GPT_4_TURBO_1106),
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=date(2023, 4, 1),
    published_at=date(2023, 11, 6),
)

AzureGpt4VisionPreview = register_language_model(
    name=LanguageModelName.AZURE_GPT_4_VISION_PREVIEW,
    provider=LanguageModelProvider.AZURE,
    version="vision-preview",
    encoder_name=get_encoder_name(LanguageModelName.AZURE_GPT_4_VISION_PREVIEW),
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=date(2023, 4, 1),
    published_at=date(2023, 11, 6),
)

AzureGpt432k0613 = register_language_model(
    name=LanguageModelName.AZURE_GPT_4_32K_0613,
    provider=LanguageModelProvider.AZURE,
    version="1106-preview",
    encoder_name=get_encoder_name(LanguageModelName.AZURE_GPT_4_32K_0613),
    token_limit=32768,
    info_cutoff_at=date(2021, 9, 1),
    published_at=date(2023, 6, 13),
    deprecated_at=date(2024, 10, 1),
    retirement_at=date(2025, 6, 1),
)

AzureGpt4Turbo20240409 = register_language_model(
    name=LanguageModelName.AZURE_GPT_4_TURBO_2024_0409,
    encoder_name=get_encoder_name(LanguageModelName.AZURE_GPT_4_TURBO_2024_0409),
    provider=LanguageModelProvider.AZURE,
    version="turbo-2024-04-09",
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=date(2023, 12, 1),
    published_at=date(2024, 4, 9),
)

AzureGpt4o20240513 = register_language_model(
    name=LanguageModelName.AZURE_GPT_4o_2024_0513,
    encoder_name=get_encoder_name(LanguageModelName.AZURE_GPT_4o_2024_0513),
    provider=LanguageModelProvider.AZURE,
    version="2024-05-13",
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=date(2023, 10, 1),
    published_at=date(2024, 5, 13),
)

AzureGpt4o20240806 = register_language_model(
    name=LanguageModelName.AZURE_GPT_4o_2024_0806,
    encoder_name=get_encoder_name(LanguageModelName.AZURE_GPT_4o_2024_0806),
    provider=LanguageModelProvider.AZURE,
    version="2024-08-06",
    token_limit_input=128000,
    token_limit_output=16384,
    info_cutoff_at=date(2023, 10, 1),
    published_at=date(2024, 8, 6),
)

AzureGpt4oMini20240718 = register_language_model(
    name=LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
    provider=LanguageModelProvider.AZURE,
    version="2024-07-18",
    encoder_name=get_encoder_name(LanguageModelName.AZURE_GPT_4o_MINI_2024_0718),
    token_limit_input=128000,
    token_limit_output=16384,
    info_cutoff_at=date(2023, 10, 1),
    published_at=date(2024, 7, 18),
)
