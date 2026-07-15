from typing import Annotated

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.default_language_model import (
    DEFAULT_LANGUAGE_MODEL,
)
from unique_toolkit.language_model.infos import LanguageModelInfo


class UserMemoryConfig(BaseModel):
    model_config = get_configuration_dict()

    use_orchestrator_language_model: bool = Field(
        default=True,
        description=(
            "When true, post-turn memory consolidation uses the orchestrator's "
            "language model and the configured 'language_model' is ignored. "
            "When false, the configured 'language_model' is used."
        ),
    )
    language_model: LMI = Field(
        default=LanguageModelInfo.from_name(DEFAULT_LANGUAGE_MODEL),
        description=(
            "The language model used for post-turn memory consolidation when "
            "'Use Orchestrator Language Model' is false."
        ),
    )
    max_tokens: int = Field(
        default=2000,
        ge=500,
        le=8000,
        description="Maximum size of the memory profile in tokens.",
    )
    consolidation_gate_enabled: bool = Field(
        default=True,
        description=(
            "When true, a cheap single-word LLM 'gate' decides whether the turn "
            "warrants a full memory rewrite before the expensive consolidation "
            "runs. Ordinary turns (small talk, questions) short-circuit as a NOOP. "
            "Set to false to always run the full consolidation call."
        ),
    )
    root_folder: Annotated[str, RJSFMetaTag.SpecialWidget.hidden()] = Field(
        default="user-memory",
        min_length=1,
        description="Root KB folder used to store per-user memory profiles.",
    )
