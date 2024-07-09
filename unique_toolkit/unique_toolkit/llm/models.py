from enum import StrEnum

from pydantic import BaseModel


class LLMModelName(StrEnum):
    AZURE_GPT_35_TURBO_0613 = "AZURE_GPT_35_TURBO_0613"
    AZURE_GPT_35_TURBO = "AZURE_GPT_35_TURBO"
    AZURE_GPT_35_TURBO_16K = "AZURE_GPT_35_TURBO_16K"
    AZURE_GPT_4_0613 = "AZURE_GPT_4_0613"
    AZURE_GPT_4_TURBO_1106 = "AZURE_GPT_4_TURBO_1106"
    AZURE_GPT_4_VISION_PREVIEW = "AZURE_GPT_4_VISION_PREVIEW"
    AZURE_GPT_4_32K_0613 = "AZURE_GPT_4_32K_0613"
    AZURE_GPT_4_TURBO_2024_0409 = "AZURE_GPT_4_TURBO_2024_0409"


class LLMModelInfo(BaseModel):
    name: LLMModelName
    max_tokens: int


llm_token_limit_map = {
    LLMModelName.AZURE_GPT_35_TURBO_0613: 3000,
    LLMModelName.AZURE_GPT_35_TURBO: 3000,
    LLMModelName.AZURE_GPT_35_TURBO_16K: 14000,
    LLMModelName.AZURE_GPT_4_0613: 7000,
    LLMModelName.AZURE_GPT_4_TURBO_1106: 7000,
    LLMModelName.AZURE_GPT_4_VISION_PREVIEW: 7000,
    LLMModelName.AZURE_GPT_4_32K_0613: 30000,
    LLMModelName.AZURE_GPT_4_TURBO_2024_0409: 7000,
}


def get_llm_model_info(model_name: LLMModelName) -> LLMModelInfo:
    if model_name not in llm_token_limit_map:
        raise ValueError(f"Model {model_name} not found.")
    return LLMModelInfo(name=model_name, max_tokens=llm_token_limit_map[model_name])
