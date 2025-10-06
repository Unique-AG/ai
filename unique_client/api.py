import generated_routes.public as unique_client
from endpoint_requestor import RequestContext
from generated_routes.components import Role

base_url = "https://gateway.qa.unique.app/public/chat-gen2"

# Simple example headers - replace with your actual auth mechanism
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "x-app-id": "YOUR_APP_ID",
    "x-company-id": "YOUR_COMPANY_ID",
    "x-user-id": "YOUR_USER_ID",
    "x-api-version": "1.0",
}

# Now using snake_case parameters! 🎉

request_context = RequestContext(base_url=base_url, headers=headers)


resp = unique_client.messages.Create.request(
    request_context,
    chat_id="test",
    assistant_id="test",
    original_text="test",
    role=Role.user,
    references=[],
    gpt_request={},
    debug_info={},
    completed_at=None,
)


resp = unique_client.folder.scopeId.Update.request(
    request_context, scope_id="test", parent_id=None, name=None
)


# Using the new client-style API (operations start with capital letter)
answer2 = unique_client.folder.CreateFolderStructure.request(
    context=request_context,
    paths=["/testcreation/test/test"],
)


# Now nested routes work too! (operations at module level)
resp = unique_client.folder.scopeId.DeleteFolder.request(
    context=request_context, scope_id="test"
)
resp.id
