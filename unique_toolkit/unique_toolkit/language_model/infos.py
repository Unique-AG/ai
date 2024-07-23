import datetime

from unique_toolkit.language_model.definition import (
    LanguageModelProvider,
    create_ai_model_info,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelName,
)

AzureGpt35Turbo0613 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_35_TURBO_0613,
    provider=LanguageModelProvider.AZURE,
    version="0613",
    token_limit=8192,
    info_cutoff_at=datetime.date(2021,9,1),
    published_at=datetime.date(2023,6,13),
    retirement_at=datetime.date(2024,10,1),
)

AzureGpt35Turbo = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_35_TURBO,
    provider=LanguageModelProvider.AZURE,
    version="0301",
    token_limit=4096,
    info_cutoff_at=datetime.date(2021,9,1),
    published_at=datetime.date(2023,3,1),
)


AzureGpt35Turbo16k = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_35_TURBO_16K,
    provider=LanguageModelProvider.AZURE,
    version="0613",
    token_limit=16382,
    info_cutoff_at=datetime.date(2021,9,1),
    published_at=datetime.date(2023,6,13),
    retirement_at=datetime.date(2024,10,1),
)


AzureGpt40613 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4_0613,
    provider=LanguageModelProvider.AZURE,
    version="0613",
    token_limit=8192,
    info_cutoff_at=datetime.date(2021,9,1),
    published_at=datetime.date(2023,6,13),
    retirement_at=datetime.date(2025,6,1),
    deprecated_at=datetime.date(2024,10,1),
)


AzureGpt4Turbo1106 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4_TURBO_1106,
    provider=LanguageModelProvider.AZURE,
    version="1106-preview",
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=datetime.date(2023,4,1),
    published_at=datetime.date(2023,11,6),
)


AzureGpt4VisionPreview = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4_VISION_PREVIEW,
    provider=LanguageModelProvider.AZURE,
    version="vision-preview",
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=datetime.date(2023,4,1),
    published_at=datetime.date(2023,11,6),
)

AzureGpt432k0613 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4_32K_0613,
    provider=LanguageModelProvider.AZURE,
    version="1106-preview",
    token_limit=32768,
    info_cutoff_at=datetime.date(2021,9,1),
    published_at=datetime.date(2023,6,13),
    retirement_at=datetime.date(2025,6,1),
    deprecated_at=datetime.date(2024,10,1),
)

AzureGpt4Turbo20240409 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4_TURBO_2024_0409,
    provider=LanguageModelProvider.AZURE,
    version="turbo-2024-04-09",
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=datetime.date(2023,12,1),
    published_at=datetime.date(2024,4,9),
)

AzureGpt4o20240513 = create_ai_model_info(
    model_name=LanguageModelName.AZURE_GPT_4o_2024_0513,
    provider=LanguageModelProvider.AZURE,
    version="2024-05-13",
    token_limit_input=128000,
    token_limit_output=4096,
    info_cutoff_at=datetime.date(2023,10,1),
    published_at=datetime.date(2024,5,13),
)
