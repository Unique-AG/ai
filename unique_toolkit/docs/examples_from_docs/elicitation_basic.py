# %%
from calendar import c
from errno import EIDRM
from re import I

from unique_sdk import User
from unique_toolkit import (
    ChatService,
    KnowledgeBaseService,
)
from pydantic import AnyUrl, BaseModel
import time
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.elicitation import (
    ElicitationCancelledException,
    ElicitationDeclinedException,
    ElicitationExpiredException,
    ElicitationMode,
    ElicitationStatus,
    ElicitationAction,
    Elicitation,
    ElicitationList
)
from typing import Any, TypeVar, overload

T = TypeVar("T", bound=BaseModel)


@overload
async def handle_elicitation(
    chat_service: ChatService,
    message: str,
    tool_name: str,
    pydantic_model_or_url: type[T],
    timeout: int = 60,
) -> T | None: ...


@overload
async def handle_elicitation(
    chat_service: ChatService,
    message: str,
    tool_name: str,
    pydantic_model_or_url: AnyUrl,
    timeout: int = 60,
) -> AnyUrl | None: ...


async def handle_elicitation(
    chat_service: ChatService,
    message: str,
    tool_name: str,
    pydantic_model_or_url: type[T] | AnyUrl,
    timeout: int = 60,
) -> AnyUrl | T | None:

    
    if isinstance(pydantic_model_or_url, AnyUrl):
        elicitation = chat_service.elicitation.create(
                mode=ElicitationMode.URL,
                url=str(pydantic_model_or_url),
                message=message,
                tool_name=tool_name,
                expires_in_seconds=timeout
            )
    else:
        elicitation = chat_service.elicitation.create(
                mode=ElicitationMode.FORM,
                message=message,
                tool_name=tool_name,
                json_schema=pydantic_model_or_url.model_json_schema(),
                expires_in_seconds=timeout
            )
        

    start = time.time()
    end_loop = False
    elicitation_result = None
    
    while not end_loop and time.time() - start < timeout:
        elicitation_result = chat_service.elicitation.get(elicitation.id)

        match elicitation_result.status:
            case ElicitationStatus.PENDING: 
                pass
            case ElicitationStatus.ACCEPTED | ElicitationStatus.CANCELLED | ElicitationStatus.EXPIRED | ElicitationStatus.DECLINED:
                end_loop = True

    if isinstance(pydantic_model_or_url, AnyUrl):
        return pydantic_model_or_url
    
    elif elicitation_result:
        return pydantic_model_or_url.model_validate(elicitation_result.response_content)


class FAQItem:
    item: str
    text: str

class TicketForm(BaseModel):
    title: str = "HR Ticket"
    email: str 

    faq: list[FAQItem] = [FAQItem(item="1", text="hello")]



async def main():

    settings = UniqueSettings.from_env_auto_with_sdk_init()
    for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
        # Initialize services from event
        chat_service = ChatService(event)
        message="Please provide the required information"
        tool_name="data_collection"

        #user_data = await handle_elicitation(chat_service, pydantic_model_or_url=UserData, timeout=60)
        #url = await handle_elicitation(
        #                                chat_service=chat_service,
        #                                message=message,
        #                                tool_name=tool_name,
        #                                pydantic_model_or_url=AnyUrl("http://samuel:pass@example.com"),
        #                                timeout=60)
        
        user_data = await handle_elicitation(
                                        chat_service=chat_service,
                                        message=message,
                                        tool_name=tool_name,
                                        pydantic_model_or_url=TicketForm,
                                        timeout=60)

        #print(url)
        print(user_data)


if __name__ == "__main__":

    import asyncio

    asyncio.run(main())


    
