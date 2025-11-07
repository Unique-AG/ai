from string import Template

from pydantic import BaseModel
from unique_toolkit._common.endpoint_builder import HttpMethods, build_api_operation
from unique_toolkit._common.endpoint_requestor import (
    RequestContext,
)

from unique_quartr.settings import quartr_settings

from .schemas import (
    PaginatedDocumentResponseDto,
    PaginatedDocumentTypeResponseDto,
    PaginatedEventResponseDto,
    PublicV3DocumentsGetParametersQuery,
    PublicV3DocumentTypesGetParametersQuery,
    PublicV3EventsGetParametersQuery,
)


class EmptyModel(BaseModel):
    ...

def get_quartr_context(*, company_id: str):
    if quartr_settings.quartr_api_creds is None:
        raise ValueError("Quartr API credentials are not set")

    if company_id not in quartr_settings.quartr_api_activated_companies:
        raise ValueError(f"Company {company_id} is not activated for Quartr API")

    return RequestContext(
        base_url="https://api.quartr.com",
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": quartr_settings.quartr_api_creds.api_key,
        },
    )


quartr_events_api_operation = build_api_operation(
    method=HttpMethods.GET,
    path_template=Template("/public/v3/events"),
    path_params_constructor=EmptyModel,
    payload_constructor=PublicV3EventsGetParametersQuery,
    response_model_type=PaginatedEventResponseDto,
)

quartr_documents_api_operation = build_api_operation(
    method=HttpMethods.GET,
    path_template=Template("/public/v3/documents"),
    path_params_constructor=EmptyModel,
    payload_constructor=PublicV3DocumentsGetParametersQuery,
    response_model_type=PaginatedDocumentResponseDto,
)

quartr_documents_types_api_operation = build_api_operation(
    method=HttpMethods.GET,
    path_template=Template("/public/v3/document-types"),
    path_params_constructor=EmptyModel,
    payload_constructor=PublicV3DocumentTypesGetParametersQuery,
    response_model_type=PaginatedDocumentTypeResponseDto,
)

quartr_api_operations = {
    "quartr_events_api": {
        "api_operation": quartr_events_api_operation,
        "combined_model": PublicV3EventsGetParametersQuery,
    },
    "quartr_documents_api": {
        "api_operation": quartr_documents_api_operation,
        "combined_model": PublicV3DocumentsGetParametersQuery,
    },
    "quartr_documents_types_api": {
        "api_operation": quartr_documents_types_api_operation,
        "combined_model": PublicV3DocumentTypesGetParametersQuery,
    },
}
