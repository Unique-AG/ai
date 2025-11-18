from logging import getLogger
from string import Template

from unique_toolkit._common.experimental.endpoint_builder import (
    HttpMethods,
    build_api_operation,
)
from unique_toolkit._common.experimental.endpoint_requestor import (
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

_LOGGER = getLogger(__name__)


def get_quartr_context(*, company_id: str):
    _LOGGER.debug(quartr_settings.model_dump_json(indent=1))
    if quartr_settings.quartr_api_creds_model is None:
        raise ValueError("Quartr API credentials are not set")

    if company_id not in quartr_settings.quartr_api_activated_companies:
        raise ValueError(f"Company {company_id} is not activated for Quartr API")

    return RequestContext(
        base_url="https://api.quartr.com",
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": quartr_settings.quartr_api_creds_model.api_key,
        },
    )


model_params_dump_options = {
    "by_alias": True,
}


QuartrEventsApiOperation = build_api_operation(
    method=HttpMethods.GET,
    path_template=Template("/public/v3/events"),
    query_params_constructor=PublicV3EventsGetParametersQuery,
    response_model_type=PaginatedEventResponseDto,
    query_params_dump_options=model_params_dump_options,
)

QuartrDocumentsApiOperation = build_api_operation(
    method=HttpMethods.GET,
    path_template=Template("/public/v3/documents"),
    query_params_constructor=PublicV3DocumentsGetParametersQuery,
    response_model_type=PaginatedDocumentResponseDto,
    query_params_dump_options=model_params_dump_options,
)

QuartrDocumentsTypesApiOperation = build_api_operation(
    method=HttpMethods.GET,
    path_template=Template("/public/v3/document-types"),
    query_params_constructor=PublicV3DocumentTypesGetParametersQuery,
    response_model_type=PaginatedDocumentTypeResponseDto,
    query_params_dump_options=model_params_dump_options,
)
