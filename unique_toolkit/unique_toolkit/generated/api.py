import unique_toolkit.generated.generated_routes.public as unique_SDK
from unique_toolkit._common.endpoint_requestor import RequestContext
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.generated.generated_routes.public.messages.models import Role

base_url = "https://gateway.qa.unique.app/public/chat-gen2"


settings = UniqueSettings.from_env_auto()
headers = {
    "Authorization": f"Bearer {settings.app.key.get_secret_value()}",
    "x-app-id": settings.app.id.get_secret_value(),
    "x-company-id": settings.auth.company_id.get_secret_value(),
    "x-user-id": settings.auth.user_id.get_secret_value(),
    "x-api-version": settings.api.version,
}


# Now using snake_case parameters! 🎉

request_context = RequestContext(headers=headers)

unique_SDK.folder.scopeId.Update.request(
    context=request_context, parent_id=None, name=None, scope_id="test"
)

unique_SDK.folder.scopeId.DeleteFolder.request(context=request_context, scope_id="test")


# Using the new client-style API (operations start with capital letter)
answer2 = unique_SDK.folder.CreateFolderStructure.request(
    context=request_context,
    paths=["/testcreation/test/test"],
)
print(answer2)
answer2 = unique_SDK.folder.CreateFolderStructure.request_async(
    context=request_context,
    paths=["/testcreation/test/test"],
)

unique_SDK.messages.Create.request(
    context=request_context,
    chat_id="test",
    assistant_id="test",
    original_text="test",
    role=Role.user,
    references=[],
    gpt_request={},
    debug_info={},
    completed_at=None,
)

# Now nested routes work too! (operations at module level)
unique_SDK.folder.scopeId.DeleteFolder.request(context=request_context, scope_id="test")
