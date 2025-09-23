from string import Template

from unique_toolkit._common.endpoint_builder import HttpMethods, build_api_operation
from unique_toolkit._common.endpoint_requestor import build_request_requestor
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.generated.generated_routes.public.folder.post.models import (
    PathParams,
    Request,
    Response,
)


class CombinedParams(PathParams, Request):
    pass


base_url = "https://gateway.qa.unique.app/public/chat-gen2"


class Folder:
    create = RequestRequestor = build_request_requestor(
        operation_type=build_api_operation(
            method=HttpMethods.POST,
            url_template=Template(base_url + "/folder"),
            path_params_constructor=PathParams,
            payload_constructor=Request,
            response_model_type=Response,
        ),
        combined_model=CombinedParams,
    )


settings = UniqueSettings.from_env_auto()
headers = {
    "Authorization": f"Bearer {settings.app.key.get_secret_value()}",
    "x-app-id": settings.app.id.get_secret_value(),
    "x-company-id": settings.auth.company_id.get_secret_value(),
    "x-user-id": settings.auth.user_id.get_secret_value(),
    "x-api-version": settings.api.version,
}


answer = Folder.create.request(headers=headers, paths=["/testcreation/test/test"])

print(answer)
