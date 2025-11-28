from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

ExtractionSchema = TypeVar("ExtractionSchema", bound=BaseModel)


class BaseDataExtractionResult(BaseModel, Generic[ExtractionSchema]):
    """
    Base class for data extraction results.
    """

    data: ExtractionSchema


class BaseDataExtractor(ABC):
    """
    Extract structured data from text.
    """

    @abstractmethod
    async def extract_data_from_text(
        self, text: str, schema: type[ExtractionSchema]
    ) -> BaseDataExtractionResult[ExtractionSchema]: ...
