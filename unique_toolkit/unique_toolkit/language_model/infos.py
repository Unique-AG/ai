from datetime import date
from enum import StrEnum
from typing import ClassVar, Optional, Self

from pydantic import BaseModel
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import deprecated

from unique_toolkit.language_model.schemas import LanguageModelTokenLimits


class LanguageModelName(StrEnum):
    AZURE_GPT_35_TURBO_0125 = "AZURE_GPT_35_TURBO_0125"
    AZURE_GPT_4_0613 = "AZURE_GPT_4_0613"
    AZURE_GPT_4_32K_0613 = "AZURE_GPT_4_32K_0613"
    AZURE_GPT_4_TURBO_2024_0409 = "AZURE_GPT_4_TURBO_2024_0409"
    AZURE_GPT_4o_2024_0513 = "AZURE_GPT_4o_2024_0513"
    AZURE_GPT_4o_2024_0806 = "AZURE_GPT_4o_2024_0806"
    AZURE_GPT_4o_2024_1120 = "AZURE_GPT_4o_2024_1120"
    AZURE_GPT_4o_MINI_2024_0718 = "AZURE_GPT_4o_MINI_2024_0718"
    AZURE_o1_MINI_2024_0912 = "AZURE_o1_MINI_2024_0912"
    AZURE_o1_2024_1217 = "AZURE_o1_2024_1217"
    AZURE_o3_MINI_2025_0131 = "AZURE_o3_MINI_2025_0131"
    AZURE_GPT_45_PREVIEW_2025_0227 = "AZURE_GPT_45_PREVIEW_2025_0227"
    AZURE_GPT_41_2025_0414 = "AZURE_GPT_41_2025_0414"
    AZURE_o3_2025_0416 = "AZURE_o3_2025_0416"
    AZURE_o4_MINI_2025_0416 = "AZURE_o4_MINI_2025_0416"
    ANTHROPIC_CLAUDE_3_7_SONNET = "litellm:anthropic-claude-3-7-sonnet"
    ANTHROPIC_CLAUDE_3_7_SONNET_THINKING = (
        "litellm:anthropic-claude-3-7-sonnet-thinking"
    )
    GEMINI_2_0_FLASH = "litellm:gemini-2-0-flash"
    GEMINI_2_5_FLASH_PREVIEW_0417 = "litellm:gemini-2-5-flash-preview-04-17"
    GEMINI_2_5_FLASH_PREVIEW_0520 = "litellm:gemini-2-5-flash-preview-05-20"
    GEMINI_2_5_PRO_EXP_0325 = "litellm:gemini-2-5-pro-exp-03-25"


class EncoderName(StrEnum):
    O200K_BASE = "o200k_base"
    CL100K_BASE = "cl100k_base"


def get_encoder_name(model_name: LanguageModelName) -> EncoderName:
    LMN = LanguageModelName
    match model_name:
        case LMN.AZURE_GPT_35_TURBO_0125:
            return EncoderName.CL100K_BASE
        case (
            LMN.AZURE_GPT_4_0613
            | LMN.AZURE_GPT_4_32K_0613
            | LMN.AZURE_GPT_4_TURBO_2024_0409
        ):
            return EncoderName.CL100K_BASE
        case (
            LMN.AZURE_GPT_4o_2024_0513
            | LMN.AZURE_GPT_4o_2024_0806
            | LMN.AZURE_GPT_4o_MINI_2024_0718
            | LMN.AZURE_GPT_4o_2024_1120
        ):
            return EncoderName.O200K_BASE
        case _:
            print(
                f"{model_name} is not supported. Please add encoder information. Using default"
            )
            return EncoderName.CL100K_BASE


class LanguageModelProvider(StrEnum):
    AZURE = "AZURE"
    CUSTOM = "CUSTOM"
    LITELLM = "LITELLM"


class ModelCapabilities(StrEnum):
    FUNCTION_CALLING = "function_calling"
    PARALLEL_FUNCTION_CALLING = "parallel_function_calling"
    REPRODUCIBLE_OUTPUT = "reproducible_output"
    STRUCTURED_OUTPUT = "structured_output"
    VISION = "vision"
    STREAMING = "streaming"
    REASONING = "reasoning"


class LanguageModelInfo(BaseModel):
    name: LanguageModelName | str
    version: str
    provider: LanguageModelProvider

    encoder_name: EncoderName = EncoderName.CL100K_BASE

    # TODO: Discuss if this is a sensible defaut
    token_limits: LanguageModelTokenLimits = LanguageModelTokenLimits(
        token_limit_input=7_000, token_limit_output=1_000
    )
    capabilities: list[ModelCapabilities] = [ModelCapabilities.STREAMING]

    info_cutoff_at: date | SkipJsonSchema[None] = None
    published_at: date | SkipJsonSchema[None] = None
    retirement_at: date | SkipJsonSchema[None] = None

    deprecated_at: date | SkipJsonSchema[None] = None
    retirement_text: str | SkipJsonSchema[None] = None

    @classmethod
    def from_name(cls, model_name: LanguageModelName) -> Self:
        match model_name:
            case LanguageModelName.AZURE_GPT_35_TURBO_0125:
                return cls(
                    name=model_name,
                    provider=LanguageModelProvider.AZURE,
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.PARALLEL_FUNCTION_CALLING,
                        ModelCapabilities.REPRODUCIBLE_OUTPUT,
                    ],
                    version="0125",
                    encoder_name=EncoderName.CL100K_BASE,
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=16385, token_limit_output=4096
                    ),
                    info_cutoff_at=date(2021, 9, 1),
                    published_at=date(2023, 1, 25),
                    retirement_at=date(5, 3, 31),
                )
            case LanguageModelName.AZURE_GPT_4_0613:
                return cls(
                    name=model_name,
                    provider=LanguageModelProvider.AZURE,
                    version="0613",
                    encoder_name=EncoderName.CL100K_BASE,
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                    ],
                    token_limits=LanguageModelTokenLimits(token_limit=8192),
                    info_cutoff_at=date(2021, 9, 1),
                    published_at=date(2023, 6, 13),
                    deprecated_at=date(2024, 10, 1),
                    retirement_at=date(2025, 6, 6),
                )
            case LanguageModelName.AZURE_GPT_4_32K_0613:
                return cls(
                    name=model_name,
                    provider=LanguageModelProvider.AZURE,
                    version="1106-preview",
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                    ],
                    encoder_name=EncoderName.CL100K_BASE,
                    token_limits=LanguageModelTokenLimits(token_limit=32768),
                    info_cutoff_at=date(2021, 9, 1),
                    published_at=date(2023, 6, 13),
                    deprecated_at=date(2024, 10, 1),
                    retirement_at=date(2025, 6, 6),
                )
            case LanguageModelName.AZURE_GPT_4_TURBO_2024_0409:
                return cls(
                    name=model_name,
                    encoder_name=EncoderName.CL100K_BASE,
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.PARALLEL_FUNCTION_CALLING,
                        ModelCapabilities.VISION,
                        ModelCapabilities.STREAMING,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="turbo-2024-04-09",
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=128000, token_limit_output=4096
                    ),
                    info_cutoff_at=date(2023, 12, 1),
                    published_at=date(2024, 4, 9),
                )
            case LanguageModelName.AZURE_GPT_4o_2024_0513:
                return cls(
                    name=model_name,
                    encoder_name=EncoderName.O200K_BASE,
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.PARALLEL_FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="2024-05-13",
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=128_000, token_limit_output=4_096
                    ),
                    info_cutoff_at=date(2023, 10, 1),
                    published_at=date(2024, 5, 13),
                )
            case LanguageModelName.AZURE_GPT_4o_2024_0806:
                return cls(
                    name=model_name,
                    encoder_name=EncoderName.O200K_BASE,
                    capabilities=[
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.PARALLEL_FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="2024-08-06",
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=128_000, token_limit_output=16_384
                    ),
                    info_cutoff_at=date(2023, 10, 1),
                    published_at=date(2024, 8, 6),
                )
            case LanguageModelName.AZURE_GPT_4o_2024_1120:
                return cls(
                    name=model_name,
                    encoder_name=EncoderName.O200K_BASE,
                    capabilities=[
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.PARALLEL_FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="2024-11-20",
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=128_000, token_limit_output=16_384
                    ),
                    info_cutoff_at=date(2023, 10, 1),
                    published_at=date(2024, 11, 20),
                )
            case LanguageModelName.AZURE_GPT_4o_MINI_2024_0718:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.PARALLEL_FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="2024-07-18",
                    encoder_name=EncoderName.O200K_BASE,
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=128_000, token_limit_output=16_384
                    ),
                    info_cutoff_at=date(2023, 10, 1),
                    published_at=date(2024, 7, 18),
                )
            case LanguageModelName.AZURE_o1_MINI_2024_0912:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                        ModelCapabilities.REASONING,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="2024-09-12",
                    encoder_name=EncoderName.O200K_BASE,
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=128_000, token_limit_output=65_536
                    ),
                    info_cutoff_at=date(2023, 10, 1),
                    published_at=date(2024, 9, 12),
                )
            case LanguageModelName.AZURE_o1_2024_1217:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                        ModelCapabilities.REASONING,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="2024-12-17",
                    encoder_name=EncoderName.O200K_BASE,
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=200_000, token_limit_output=100_000
                    ),
                    info_cutoff_at=date(2023, 10, 1),
                    published_at=date(2024, 12, 17),
                )
            case LanguageModelName.AZURE_o3_MINI_2025_0131:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.REASONING,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="2025-01-31",
                    encoder_name=EncoderName.O200K_BASE,
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=200_000, token_limit_output=100_000
                    ),
                    info_cutoff_at=date(2023, 10, 1),
                    published_at=date(2025, 1, 31),
                )
            case LanguageModelName.AZURE_o3_2025_0416:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.REASONING,
                        ModelCapabilities.VISION,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="2025-04-16",
                    encoder_name=EncoderName.O200K_BASE,
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=200_000, token_limit_output=100_000
                    ),
                    info_cutoff_at=date(2024, 5, 31),
                    published_at=date(2025, 4, 16),
                )
            case LanguageModelName.AZURE_o4_MINI_2025_0416:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.REASONING,
                        ModelCapabilities.VISION,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="2025-04-16",
                    encoder_name=EncoderName.O200K_BASE,
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=200_000, token_limit_output=100_000
                    ),
                    info_cutoff_at=date(2024, 5, 31),
                    published_at=date(2025, 4, 16),
                )
            case LanguageModelName.AZURE_GPT_45_PREVIEW_2025_0227:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="2025-02-27",
                    encoder_name=EncoderName.O200K_BASE,
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=128_000, token_limit_output=16_384
                    ),
                    info_cutoff_at=date(2023, 10, 1),
                    published_at=date(2025, 2, 27),
                )
            case LanguageModelName.AZURE_GPT_41_2025_0414:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                    ],
                    provider=LanguageModelProvider.AZURE,
                    version="2025-04-14",
                    encoder_name=EncoderName.O200K_BASE,
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=1_047_576, token_limit_output=32_768
                    ),
                    info_cutoff_at=date(2024, 5, 31),
                    published_at=date(2025, 4, 14),
                )
            case LanguageModelName.ANTHROPIC_CLAUDE_3_7_SONNET:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                    ],
                    provider=LanguageModelProvider.LITELLM,
                    version="claude-3-7-sonnet",
                    encoder_name=EncoderName.O200K_BASE,  # TODO: Update encoder with litellm
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=200_000, token_limit_output=128_000
                    ),
                    info_cutoff_at=date(2024, 10, 31),
                    published_at=date(2025, 2, 24),
                )
            case LanguageModelName.ANTHROPIC_CLAUDE_3_7_SONNET_THINKING:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                        ModelCapabilities.REASONING,
                    ],
                    provider=LanguageModelProvider.LITELLM,
                    version="claude-3-7-sonnet-thinking",
                    encoder_name=EncoderName.O200K_BASE,  # TODO: Update encoder with litellm
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=200_000, token_limit_output=128_000
                    ),
                    info_cutoff_at=date(2024, 10, 31),
                    published_at=date(2025, 2, 24),
                )
            case LanguageModelName.GEMINI_2_0_FLASH:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.REASONING,
                    ],
                    provider=LanguageModelProvider.LITELLM,
                    version="gemini-2-0-flash",
                    encoder_name=EncoderName.O200K_BASE,  # TODO: Update encoder with litellm
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=1_048_576, token_limit_output=8_192
                    ),
                    info_cutoff_at=date(2024, 8, 1),
                    published_at=date(2025, 2, 1),
                )
            case LanguageModelName.GEMINI_2_5_FLASH_PREVIEW_0417:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.REASONING,
                    ],
                    provider=LanguageModelProvider.LITELLM,
                    version="gemini-2-5-flash-preview-04-17",
                    encoder_name=EncoderName.O200K_BASE,  # TODO:Replace with LLM tokenizer
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=1_048_576, token_limit_output=65_536
                    ),
                    info_cutoff_at=date(2025, 1, day=1),
                    published_at=date(2025, 4, 1),
                )
            case LanguageModelName.GEMINI_2_5_FLASH_PREVIEW_0520:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.REASONING,
                    ],
                    provider=LanguageModelProvider.LITELLM,
                    version="gemini-2-5-flash-preview-05-20",
                    encoder_name=EncoderName.O200K_BASE,  # TODO:Replace with LLM tokenizer
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=1_048_576, token_limit_output=65_536
                    ),
                    info_cutoff_at=date(2025, 1, day=1),
                    published_at=date(2025, 4, 1),
                )
            case LanguageModelName.GEMINI_2_5_PRO_EXP_0325:
                return cls(
                    name=model_name,
                    capabilities=[
                        ModelCapabilities.FUNCTION_CALLING,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.VISION,
                        ModelCapabilities.STRUCTURED_OUTPUT,
                        ModelCapabilities.REASONING,
                    ],
                    provider=LanguageModelProvider.LITELLM,
                    version="gemini-2-5-pro-exp-0325",
                    encoder_name=EncoderName.O200K_BASE,  # TODO: Update encoder with litellm
                    token_limits=LanguageModelTokenLimits(
                        token_limit_input=1_048_576, token_limit_output=65_536
                    ),
                    info_cutoff_at=date(2025, 1, day=1),
                    published_at=date(2025, 3, 1),
                )
            case _:
                if isinstance(model_name, LanguageModelName):
                    raise ValueError(
                        f"{model_name} is not supported. Please add model information in toolkit."
                    )

                return cls(
                    name=model_name,
                    version="custom",
                    provider=LanguageModelProvider.CUSTOM,
                )

    @property
    def display_name(self) -> str:
        """
        Returns the name of the model as a string.
        """

        if isinstance(self.name, LanguageModelName):
            return self.name.value
        else:
            return self.name


@deprecated(
    """
Use `LanguageModelInfo` instead of `LanguageModel`.

`LanguageModel` will be deprecated on 31.12.2025
""",
)
class LanguageModel:
    _info: ClassVar[LanguageModelInfo]

    def __init__(self, model_name: LanguageModelName | str):
        self._model_info = self.get_model_info(model_name)

    @property
    def info(self) -> LanguageModelInfo:
        """Return all infos about the model.

        - name
        - version
        - provider
        - encoder_name
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
    def encoder_name(self) -> Optional[EncoderName]:
        """
        Returns the encoder_name used for the model.
        """
        return self._model_info.encoder_name

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
        if isinstance(model_name, LanguageModelName):
            return LanguageModelInfo.from_name(model_name)

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
            LanguageModelInfo.from_name(model_name=name) for name in LanguageModelName
        ]
