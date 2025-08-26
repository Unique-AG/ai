from enum import StrEnum
from typing import Any

from pydantic import Field

from unique_stock_ticker.clients.six.schema.common.base.model import BaseAPIModel


class ErrorCategory(StrEnum):
    ENTITLEMENT_ERROR = "ENTITLEMENT_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    DATA_FETCHING_ERROR = "DATA_FETCHING_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    OTHER = "OTHER"


class ErrorCode(StrEnum):
    ACCESS_DENIED = "ACCESS_DENIED"
    TIMEOUT = "TIMEOUT"
    INVALID_PERIOD = "INVALID_PERIOD"
    INVALID_RANGE = "INVALID_RANGE"
    INVALID_CRITERIA = "INVALID_CRITERIA"
    NO_DATA = "NO_DATA"
    PARAMETER_NOT_READABLE = "PARAMETER_NOT_READABLE"
    PARAMETER_REQUIRED = "PARAMETER_REQUIRED"
    DATA_REPORT_ERROR = "DATA_REPORT_ERROR"
    QUOTA_LIMIT_EXCEEDED = "QUOTA_LIMIT_EXCEEDED"
    INTERNAL_SERVICE_ERROR = "INTERNAL_SERVICE_ERROR"
    REQUEST_NOT_ALLOWED = "REQUEST_NOT_ALLOWED"
    TOO_MANY_OPERATIONS = "TOO_MANY_OPERATIONS"
    DUPLICATE_STREAM_ID = "DUPLICATE_STREAM_ID"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    OTHER = "OTHER"


class HintType(StrEnum):
    ALLOWED_RANGE = "ALLOWED_RANGE"
    ALLOWED_VALUES = "ALLOWED_VALUES"
    CONTACT_SIX = "CONTACT_SIX"


class Explain(BaseAPIModel):
    query: str
    variables: dict[str, dict[str, Any]]


class DataStatus(BaseAPIModel):
    top_level: str | None = None
    data_status: list[dict[str, Any]] | None = None
    empty: bool | None = None


class DatasetIds(BaseAPIModel):
    top_level: str | None = None
    dataset_ids: list[dict[str, Any]] | None = None
    empty: bool | None = None


class Details(BaseAPIModel):
    correlation_id: str | None = None
    user_id: str | None = None


class ExtensionsData(BaseAPIModel):
    explain: Explain | None = None
    data_status: DataStatus | None = None
    dataset_ids: DatasetIds | None = None
    details: Details | None = None


class ErrorHint(BaseAPIModel):
    type: HintType
    data: dict[str, Any]


class ErrorDetail(BaseAPIModel):
    category: ErrorCategory = Field(
        description="Error categories", examples=["VALIDATION_ERROR"]
    )
    code: ErrorCode = Field(
        description="code is used to identify the error",
        examples=["CANNOT_CONVERT_PARAMETER"],
    )
    message: str = Field(
        ...,
        description="a human readable description of the error",
        examples=["missing header 'X-HEADER'"],
    )
    hint: ErrorHint | None = None


class BaseResponsePayload(BaseAPIModel):
    errors: list[ErrorDetail] | None = None
    extensions: ExtensionsData | None = None
