from enum import StrEnum
from logging import getLogger
from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from unique_toolkit.tools.config import get_configuration_dict

logger = getLogger(__name__)


class ContentProcessingStartegy(StrEnum):
    SUMMARIZE = "summarize"
    TRUNCATE = "truncate"


T = TypeVar("T", bound=ContentProcessingStartegy)


class ContentProcessingStrategyConfig(BaseModel, Generic[T]):
    model_config = get_configuration_dict()

    strategy: T = Field(
        description="The strategy to use for content processing",
    )
