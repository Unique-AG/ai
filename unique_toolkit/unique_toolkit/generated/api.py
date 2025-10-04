from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.generated.generated_routes.public.folder import Folder
from unique_toolkit.generated.generated_routes.public.folder.scopeId import ScopeId

base_url = "https://gateway.qa.unique.app/public/chat-gen2"


settings = UniqueSettings.from_env_auto()
headers = {
    "Authorization": f"Bearer {settings.app.key.get_secret_value()}",
    "x-app-id": settings.app.id.get_secret_value(),
    "x-company-id": settings.auth.company_id.get_secret_value(),
    "x-user-id": settings.auth.user_id.get_secret_value(),
    "x-api-version": settings.api.version,
}

answer = Folder.createFolderStructure.request(
    headers=headers,
    paths=["/testcreation/test/test"],
)

# Now using snake_case parameters! 🎉
ScopeId.deleteFolder.request(headers=headers, scope_id="test")

ScopeId.update.request(headers=headers, parent_id=None, name=None, scope_id="test")
ScopeId.deleteFolder.request(headers=headers, scope_id="test")
print(answer)
