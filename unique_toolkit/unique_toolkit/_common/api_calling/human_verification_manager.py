import hashlib
from datetime import datetime
from logging import Logger
from typing import Any, Generic

import jinja2
from pydantic import BaseModel

from unique_toolkit._common.endpoint_builder import (
    ApiOperationProtocol,
    PathParamsSpec,
    PathParamsType,
    PayloadParamSpec,
    PayloadType,
    ResponseType,
)
from unique_toolkit._common.endpoint_requestor import (
    RequestContext,
    RequestorType,
    build_requestor,
)
from unique_toolkit._common.pydantic_helpers import (
    create_complement_model,
    create_union_model,
)
from unique_toolkit._common.string_utilities import (
    dict_to_markdown_table,
    extract_dicts_from_string,
)
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole


class HumanConfirmation(BaseModel):
    payload_hash: str
    time_stamp: datetime


NEXT_USER_MESSAGE_JINJA2_TEMPLATE = jinja2.Template("""I confirm the api call with the following data:
```json
{{ api_call_as_json }}
```""")


ASSISTANT_CONFIRMATION_MESSAGE_JINJA2_TEMPLATE = jinja2.Template("""I would like to call the api with the following data:

{{ api_call_as_markdown_table }}

[{{ button_text }}](https://prompt={{ next_user_message | urlencode }})""")


class HumanVerificationManagerForApiCalling(
    Generic[
        PathParamsSpec,
        PathParamsType,
        PayloadParamSpec,
        PayloadType,
        ResponseType,
    ]
):
    """
    Manages human verification for api calling.

    The idea is that the manager is able to produce the verification message to the user
    and to detect an api call from the user message.

    If it detects such a verification message in the user message, it will call the api
    and incorporate the response into the user message.
    """

    def __init__(
        self,
        *,
        logger: Logger,
        operation: type[
            ApiOperationProtocol[
                PathParamsSpec,
                PathParamsType,
                PayloadParamSpec,
                PayloadType,
                ResponseType,
            ]
        ],
        requestor_type: RequestorType = RequestorType.REQUESTS,
        environment_params: BaseModel | None = None,
        **kwargs: dict[str, Any],
    ):
        self._logger = logger
        self._operation = operation
        self._environment_params = environment_params
        # Create internal models for this manager instance

        self._combined_params_model = create_union_model(
            model_type_a=self._operation.path_params_model(),
            model_type_b=self._operation.payload_model(),
        )

        if self._environment_params is None:
            self._modifiable_params_model = self._operation.payload_model()
        else:
            self._modifiable_params_model = create_complement_model(
                model_type_a=self._operation.payload_model(),
                model_type_b=type(self._environment_params),
            )

        class VerificationModel(BaseModel):
            confirmation: HumanConfirmation
            modifiable_params: self._modifiable_params_model  # type: ignore

        self._verification_model = VerificationModel

        self._requestor_type = requestor_type
        self._requestor = build_requestor(
            requestor_type=requestor_type,
            operation_type=operation,
            combined_model=self._combined_params_model,
            **kwargs,
        )

    def detect_api_calls_from_user_message(
        self,
        *,
        last_assistant_message: ChatMessage,
        user_message: str,
    ) -> PayloadType | None:
        user_message_dicts = extract_dicts_from_string(user_message)
        if len(user_message_dicts) == 0:
            return None

        user_message_dicts.reverse()
        for user_message_dict in user_message_dicts:
            try:
                # Convert dict to payload model first, then create payload
                verfication_data = self._verification_model.model_validate(
                    user_message_dict, by_alias=True, by_name=True
                )
                if self._verify_human_verification(
                    verfication_data.confirmation, last_assistant_message
                ):
                    payload_dict = verfication_data.modifiable_params.model_dump()
                    if self._environment_params is not None:
                        payload_dict.update(self._environment_params.model_dump())

                    return self._operation.payload_model().model_validate(payload_dict)

            except Exception as e:
                self._logger.error(f"Error detecting api calls from user message: {e}")

        return None

    def _verify_human_verification(
        self, confirmation: HumanConfirmation, last_assistant_message: ChatMessage
    ) -> bool:
        if (
            last_assistant_message.role != ChatMessageRole.ASSISTANT
            or last_assistant_message.content is None
        ):
            self._logger.error(
                "Last assistant message is not an assistant message or content is empty."
            )
            return False

        return confirmation.payload_hash in last_assistant_message.content

    def _create_next_user_message(self, payload: PayloadType) -> str:
        # Extract only the modifiable fields from the payload
        payload_dict = payload.model_dump()
        if self._environment_params is not None:
            # Remove environment params from payload to avoid validation errors
            environment_fields = set(type(self._environment_params).model_fields.keys())
            modifiable_dict = {
                k: v for k, v in payload_dict.items() if k not in environment_fields
            }
        else:
            modifiable_dict = payload_dict

        modifiable_params = self._modifiable_params_model.model_validate(
            modifiable_dict
        )
        api_call = self._verification_model(
            modifiable_params=modifiable_params,
            confirmation=HumanConfirmation(
                payload_hash=hashlib.sha256(
                    modifiable_params.model_dump_json().encode()
                ).hexdigest(),
                time_stamp=datetime.now(),
            ),
        )
        return NEXT_USER_MESSAGE_JINJA2_TEMPLATE.render(
            api_call_as_json=api_call.model_dump_json(indent=2)
        )

    def create_assistant_confirmation_message(self, *, payload: PayloadType) -> str:
        return ASSISTANT_CONFIRMATION_MESSAGE_JINJA2_TEMPLATE.render(
            api_call_as_markdown_table=dict_to_markdown_table(payload.model_dump()),
            button_text="Please confirm the call by pressing this button.",
            next_user_message=self._create_next_user_message(payload),
        )

    def call_api(
        self,
        *,
        context: RequestContext,
        path_params: PathParamsType,
        payload: PayloadType,
    ) -> ResponseType:
        """
        Call the api with the given path params, payload and secured payload params.

        The `secured payload params` are params that are enforced by the application.
        It should generally be not possible for the user to adapt those but here we
        ensure that the application has the last word.

        """
        params = path_params.model_dump()
        params.update(payload.model_dump())

        response = self._requestor.request(
            context=context,
            **params,
        )
        return self._operation.handle_response(response)


if __name__ == "__main__":
    import logging
    from string import Template

    from unique_toolkit._common.endpoint_builder import (
        EndpointMethods,
        build_api_operation,
    )

    class GetUserPathParams(BaseModel):
        user_id: int

    class GetUserRequestBody(BaseModel):
        include_profile: bool = False

    class UserResponse(BaseModel):
        id: int
        name: str

    class CombinedParams(GetUserPathParams, GetUserRequestBody):
        pass

    UserEndpoint = build_api_operation(
        method=EndpointMethods.GET,
        url_template=Template("https://api.example.com/users/{user_id}"),
        path_params_constructor=GetUserPathParams,
        payload_constructor=GetUserRequestBody,
        response_model_type=UserResponse,
    )

    human_verification_manager = HumanVerificationManagerForApiCalling(
        logger=logging.getLogger(__name__),
        operation=UserEndpoint,
        requestor_type=RequestorType.FAKE,
        return_value={"id": 100, "name": "John Doe"},
    )

    payload = GetUserRequestBody(include_profile=True)

    api_call = human_verification_manager._verification_model(
        modifiable_params=payload,
        confirmation=HumanConfirmation(
            payload_hash=hashlib.sha256(payload.model_dump_json().encode()).hexdigest(),
            time_stamp=datetime.now(),
        ),
    )

    last_assistant_message = ChatMessage(
        role=ChatMessageRole.ASSISTANT,
        text=api_call.confirmation.payload_hash,
        chat_id="123",
    )

    user_message_with_api_call = human_verification_manager._create_next_user_message(
        payload=payload
    )

    print(user_message_with_api_call)

    payload = human_verification_manager.detect_api_calls_from_user_message(
        user_message=user_message_with_api_call,
        last_assistant_message=last_assistant_message,
    )

    if payload is None:
        print("❌ Detection failed - payload is None")
        exit(1)
    else:
        print("✅ Detection successful!")
        print(f"Payload: {payload.model_dump()}")
        print("✅ Dict extraction from string works correctly!")
