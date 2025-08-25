from enum import StrEnum

from pydantic import Field

from unique_stock_ticker.clients.six.schema.common.base.model import BaseAPIModel
from unique_stock_ticker.clients.six.schema.common.language import Language


class RequestExtension(StrEnum):
    EXPLAIN = "EXPLAIN"
    DATA_STATUS = "DATA_STATUS"
    DATASET_IDS = "DATASET_IDS"


class BaseRequestParams(BaseAPIModel):
    preferred_language: Language = Field(default=Language.EN)
    extensions: list[RequestExtension] = Field(default=[])
