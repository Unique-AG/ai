from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from core.schema import (
    SearchEngineType,
    SearchRequest,
    camelized_model_config,
)


class ThreatSkillType(StrEnum):
    INDIRECT_PROMPT_INJECTION = "indirect_prompt_injection"
    LOCALHOST_ACCESS = "localhost_access"
    DATA_EXFILTRATION = "data_exfiltration"


class ThreatSkillDefinition(BaseModel):
    """Schema for a threat skill. Matches the YAML structure of predefined threats."""

    model_config = camelized_model_config

    name: str = Field(description="Human-readable threat name")
    description: str = Field(description="What this threat models")
    system_prompt: str = Field(
        description="System prompt instructing the LLM how to generate the malicious content"
    )


class MaliciousSearchParams(BaseModel):
    model_config = camelized_model_config

    fetch_size: int = Field(
        default=5, ge=1, le=20, description="Number of results to generate"
    )
    threat_rate: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Probability [0-1] that a given result is malicious vs benign",
    )
    model_name: str = Field(default="AZURE_GPT_4o_2024_1120")

    enabled_threats: list[ThreatSkillType] | None = Field(
        default=None,
        description="Predefined threats to activate (StrEnum values). None = all predefined threats.",
    )
    custom_threats: list[ThreatSkillDefinition] | None = Field(
        default=None,
        description="Ad-hoc threat definitions provided inline in the request.",
    )


class MaliciousSearchRequest(
    SearchRequest[SearchEngineType.MALICIOUS, MaliciousSearchParams]
):
    model_config = camelized_model_config
    search_engine: Literal[SearchEngineType.MALICIOUS] = SearchEngineType.MALICIOUS
    params: MaliciousSearchParams = Field(
        default_factory=MaliciousSearchParams,
        description="Parameters for the malicious search engine",
    )
