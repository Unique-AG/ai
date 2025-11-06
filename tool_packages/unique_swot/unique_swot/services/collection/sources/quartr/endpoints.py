from jinja2 import Template
from pydantic import BaseModel
from unique_toolkit._common.endpoint_builder import HttpMethods, build_api_operation
from unique_toolkit._common.endpoint_requestor import (
    RequestContext,
    build_httpx_requestor,
)

from unique_swot.services.collection.sources.quartr.schemas import (
    PaginatedDocumentResponseDto,
    PaginatedDocumentTypeResponseDto,
    PaginatedEventResponseDto,
    PublicV3DocumentsGetParametersQuery,
    PublicV3DocumentTypesGetParametersQuery,
    PublicV3EventsGetParametersQuery,
)


class NoPathParams(BaseModel): ...

def get_quartr_context(company_id: str = ""):
    return RequestContext(
        base_url="https://api.quartr.com",
        headers={"Content-Type": "application/json", "X-Api-Key": "xxx"},
    )


quartr_events_requestor = build_httpx_requestor(
    operation_type=build_api_operation(
        method=HttpMethods.GET,
        path_template=Template("/public/v3/events"),
        path_params_constructor=NoPathParams,
        payload_constructor=PublicV3EventsGetParametersQuery,
        response_model_type=PaginatedEventResponseDto,
    ),
    combined_model=PublicV3EventsGetParametersQuery,
)()


quartr_documents_requestor = build_httpx_requestor(
    operation_type=build_api_operation(
        method=HttpMethods.GET,
        path_template=Template("/public/v3/events"),
        path_params_constructor=NoPathParams,
        payload_constructor=PublicV3DocumentsGetParametersQuery,
        response_model_type=PaginatedDocumentResponseDto,
    ),
    combined_model=PublicV3DocumentsGetParametersQuery,
)()


quartr_documents_requestor = build_httpx_requestor(
    operation_type=build_api_operation(
        method=HttpMethods.GET,
        path_template=Template("/public/v3/events"),
        path_params_constructor=NoPathParams,
        payload_constructor=PublicV3DocumentTypesGetParametersQuery,
        response_model_type=PaginatedDocumentTypeResponseDto,
    ),
    combined_model=PublicV3DocumentTypesGetParametersQuery,
)()