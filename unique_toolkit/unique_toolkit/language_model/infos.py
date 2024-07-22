from unique_toolkit.language_model.definition import (
    LanguageModelProvider,
    create_ai_model_info,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelName,
)

# TODO add
# - max_tokens
# - tokens_per_min
# - info_cutoff_at
# - published_at
# - retirement_at
AzureGpt35Turbo0613 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_35_TURBO_0613,
    token_limit=3000,
    provider=LanguageModelProvider.AZURE,
)

# TODO add
# - max_tokens
# - tokens_per_min
# - info_cutoff_at
# - published_at
# - retirement_at
AzureGpt35Turbo = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_35_TURBO,
    token_limit=3000,
    provider=LanguageModelProvider.AZURE,
    deprecated=True,
    deprecated_text="Use AzureGpt35Turbo0613 instead.",
)

# TODO add
# - max_tokens
# - tokens_per_min
# - info_cutoff_at
# - published_at
# - retirement_at
AzureGpt35Turbo16k = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_35_TURBO_16K,
    token_limit=14000,
    provider=LanguageModelProvider.AZURE,
)

# TODO add
# - max_tokens
# - tokens_per_min
# - info_cutoff_at
# - published_at
# - retirement_at
AzureGpt40613 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4_0613,
    token_limit=7000,
    provider=LanguageModelProvider.AZURE,
)

# TODO add
# - max_tokens
# - tokens_per_min
# - info_cutoff_at
# - published_at
# - retirement_at
AzureGpt4Turbo1106 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4_TURBO_1106,
    token_limit=7000,
    provider=LanguageModelProvider.AZURE,
)

# TODO add
# - max_tokens
# - tokens_per_min
# - info_cutoff_at
# - published_at
# - retirement_at
AzureGpt4VisionPreview = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4_VISION_PREVIEW,
    token_limit=7000,
    provider=LanguageModelProvider.AZURE,
)

# TODO add
# - max_tokens
# - tokens_per_min
# - info_cutoff_at
# - published_at
# - retirement_at
AzureGpt432k0613 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4_32K_0613,
    token_limit=30000,
    provider=LanguageModelProvider.AZURE,
)

# TODO add
# - max_tokens
# - tokens_per_min
# - info_cutoff_at
# - published_at
# - retirement_at
AzureGpt4Turbo20240409 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4_TURBO_2024_0409,
    token_limit=7000,
    provider=LanguageModelProvider.AZURE,
)

# TODO add
# - max_tokens
# - tokens_per_min
# - info_cutoff_at
# - published_at
# - retirement_at
AzureGpt4o20240513 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4o_2024_0513,
    token_limit=7000,
    provider=LanguageModelProvider.AZURE,
)
