import unique_toolkit.generated.generated_routes.public as uniquq_SDK
from unique_toolkit._common.endpoint_requestor import RequestContext
from unique_toolkit.app.unique_settings import UniqueSettings

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

uniquq_SDK.folder.scopeId.Update.request(
    context=request_context, parent_id=None, name=None, scope_id="test"
)

uniquq_SDK.folder.scopeId.DeleteFolder.request(context=request_context, scope_id="test")


# Using the new client-style API (operations start with capital letter)
answer2 = uniquq_SDK.folder.CreateFolderStructure.request(
    context=request_context,
    paths=["/testcreation/test/test"],
)
print(answer2)

# Now nested routes work too! (operations at module level)
uniquq_SDK.folder.scopeId.DeleteFolder.request(context=request_context, scope_id="test")
