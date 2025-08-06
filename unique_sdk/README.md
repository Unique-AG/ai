# Unique Python SDK

Unique FinanceGPT is a tailored solution for the financial industry, designed to increase productivity by automating manual workloads through AI and ChatGPT solutions.

The Unique Python SDK provides access to the public API of Unique FinanceGPT. It also enables verification of Webhook signatures to ensure the authenticity of incoming Webhook requests.

## Table of Contents

1. [Installation](#installation)
2. [Requirements](#requirements)
3. [Usage Instructions](#usage-instructions)
4. [Webhook Triggers](#webhook-triggers)
5. [Available API Resources](#available-api-resources)
   - [Content](#content)
   - [Message](#message)
   - [Chat Completion](#chat-completion)
   - [Embeddings](#embeddings)
   - [Acronyms](#acronyms)
   - [Search](#search)
   - [Search String](#search-string)
   - [Short Term Memory](#short-term-memory)
   - [Message Assessment](#message-assessment)
   - [Folder](#folder)
   - [Space](#space)
6. [UniqueQL](#uniqueql)
   - [Query Structure](#uniqueql-query-structure)
   - [Metadata Filtering](#metadata-filtering)
7. [Util functions](#utils)
   - [Chat History](#chat-history)
   - [File Io](#file-io)
   - [Sources](#sources)
   - [token](#token)
   - [Chat In Space](#chat-in-space)
8. [Error Handling](#error-handling)
9. [Examples](#examples)

## Installation

Install UniqueSDK and its peer dependency `requests` and when planning to run async requests also `httpx` or `aiohttp` via pip using the following commands:

```bash
pip install unique_sdk
pip install requests
```

Optional for async requests:

```bash
pip install httpx
```

or

```bash
pip install aiohttp
```

## Requirements

- Python >=3.11 (Other Python versions 3.6+ might work but are not tested)
- requests (peer dependency. Other HTTP request libraries might be supported in the future)
- Unique App-ID & API Key

Please contact your customer success manager at Unique for your personal developer App-ID & API Key.

## Usage instructions

The library needs to be configured with your Unique `app_id` & `api_key`. Additionally, each individual request must be scoped to a User and provide a `user_id` & `company_id`.

```python
import unique_sdk
unique_sdk.api_key = "ukey_..."
unique_sdk.app_id = "app_..."
```

The SDK includes a set of classes for API resources. Each class contains CRUD methods to interact with the resource.

### Example

```python
import unique_sdk
unique_sdk.api_key = "ukey_..."
unique_sdk.app_id = "app_..."

# list messages for a single chat
messages = unique_sdk.Message.list(
    user_id=user_id,
    company_id=company_id,
    chatId=chat_id,
)

print(messages.data[0].text)
```

## Webhook Triggers

A core functionality of FinanceGPT is the ability for users to engage in an interactive chat feature. SDK developers can hook into this chat to provide new functionalities.

Your App (refer to `app-id` in [Requirements](#requirements)) must be subscribed to each individual Unique event in order to receive a webhook.

Each webhook sent by Unique includes a set of headers:

```yaml
X-Unique-Id: evt_... # Event id, same as in the body.
X-Unique-Signature: ... # A HMAC-SHA256 hex signature of the entire body.
X-Unique-Version: 1.0.0 # Event payload version.
X-Unique-Created-At: 1705960141 # Unix timestamp (seconds) of the delivery time.
X-Unique-User-Id: ... # The user who initiated the message.
X-Unique-Company-Id: ... # The company to which the user belongs.
```

### Success & Retry on Failure

- Webhooks are considered successfully delivered if your endpoint returns a status code between `200` and `299`.
- If your endpoint returns a status code of `300` - `399`, `429`, or `500` - `599`, Unique will retry the delivery of the webhook with an exponential backoff up to five times.
- If your endpoint returns any other status (e.g., `404`), it is marked as expired and will not receive any further requests.

### Webhook Signature Verification

The webhook body, containing a timestamp of the delivery time, is signed with HMAC-SHA256. Verify the signature by constructing the `event` with the `unique_sdk.Webhook` class:

```python
from http import HTTPStatus
from flask import Flask, jsonify, request
import unique_sdk

endpoint_secret = "YOUR_ENDPOINT_SECRET"

@app.route("/webhook", methods=["POST"])
def webhook():
    event = None
    payload = request.data

    sig_header = request.headers.get("X-Unique-Signature")
    timestamp = request.headers.get("X-Unique-Created-At")

    if not sig_header or not timestamp:
        print("⚠️  Webhook signature or timestamp headers missing.")
        return jsonify(success=False), HTTPStatus.BAD_REQUEST

    try:
        event = unique_sdk.Webhook.construct_event(
            payload, sig_header, timestamp, endpoint_secret
        )
    except unique_sdk.SignatureVerificationError as e:
        print("⚠️  Webhook signature verification failed. " + str(e))
        return jsonify(success=False), HTTPStatus.BAD_REQUEST
```

The `construct_event` method will compare the signature and raise a `unique_sdk.SignatureVerificationError` if the signature does not match. It will also raise this error if the `createdAt` timestamp is outside of a default tolerance of 5 minutes. Adjust the `tolerance` by passing a fifth parameter to the method (tolerance in seconds), e.g.:

```python
event = unique_sdk.Webhook.construct_event(
    payload, sig_header, timestamp, endpoint_secret, 0
)
```

### Available Unique Events

#### User Message Created

```json
{
  "id": "evt_...", // see header
  "version": "1.0.0", // see header
  "event": "unique.chat.user-message.created", // The name of the event
  "createdAt": "1705960141", // see header
  "userId": "...", // see header
  "companyId": "...", // see header
  "payload": {
    "chatId": "chat_...", // The id of the chat
    "assistantId": "assistant_...", // The id of the selected assistant
    "text": "Hello, how can I help you?" // The user message
  }
}
```

This webhook is triggered for every new chat message sent by the user. This event occurs regardless of whether it is the first or a subsequent message in a chat. Use the `unique_sdk.Message` class to retrieve other messages from the same `chatId` or maintain a local state of the messages in a single chat.

This trigger can be used in combination with assistants marked as `external`. Those assistants will not execute any logic, enabling your code to respond to the user message and create an answer.

#### External Module Chosen

```json
{
  "id": "evt_...",
  "version": "1.0.0",
  "event": "unique.chat.external-module.chosen",
  "createdAt": "1705960141", // Unix timestamp (seconds)
  "userId": "...",
  "companyId": "...",
  "payload": {
    "name": "example-sdk", // The name of the module selected by the module chooser
    "description": "Example SDK", // The description of the module
    "configuration": {}, // Module configuration in JSON format
    "chatid": "chat_...", // The chat ID
    "assistantId:": "assistant_...", // The assistant ID
    "userMessage": {
      "id": "msg_...",
      "text": "Hello World!", // The user message leading to the module selection
      "createdAt": "2024-01-01T00:00:00.000Z" // ISO 8601
    },
    "assistantMessage": {
      "id": "msg_...",
      "createdAt": "2024-01-01T00:00:00.000Z" // ISO 8601
    }
  }
}
```

This Webhook is triggered when the Unique FinanceGPT AI selects an external module as the best response to a user message. The module must be marked as `external` and available for the assistant used in the chat to be selected by the AI.

Unique's UI will create an empty `assistantMessage` below the user message and update this message with status updates.

**The SDK is expected to modify this assistantMessage with its answer to the user message.**

```python
unique_sdk.Message.modify(
    user_id=user_id,
    company_id=company_id,
    id=assistant_message_id,
    chatId=chat_id,
    text="Here is your answer.",
)
```

## Available API Resources

- [Content](#content)
- [Message](#message)
- [Chat Completion](#chat-completion)
- [Embeddings](#embeddings)
- [Acronyms](#acronyms)
- [Search](#search)
- [Search String](#search-string)
- [Short Term Memory](#short-term-memory)
- [Message Assessment](#message-assessment)
- [Folder](#folder)
- [Space](#space)

Most of the API services provide an asynchronous version of the method. The async methods are suffixed with `_async`.

### Content

#### `unique_sdk.Content.search`

Allows you to load full content/files from the knowledge-base of unique with the rights of the userId and companyId. Provided a `where` query for filtering. Filtering can be done on any of the following fields: `

- `id`
- `key`
- `ownerId`
- `title`
- `url`

Here an example of retrieving all files that contain the number 42 in the `title` or the `key` typically this is used to search by filename.

```python
unique_sdk.Content.search(
    user_id=userId,
    company_id=companyId,
    where={
        "OR": [
            {
                "title": {
                    "contains": "42",
                },
            },
            {
                "key": {
                    "contains": "42",
                },
            },
        ],
    },
    chatId=chatId,
)
```

#### `unique_sdk.Content.get_info`

[Deprecated, use `unique_sdk.Content.get_infos` instead.] Allows you to get content info. To filter the results you can define a metadata filter in UniqueQL language. Find out more about it in the UniqueQL section. An example of a metadata filter defined with UniqueQL is the following:

```python
    metadataFilter: {
        "or": [
            {
                "and": [
                    {
                        "operator": "contains",
                        "path": [
                            "folderIdPath"
                        ],
                        "value": "uniquepathid://test_id"
                    },
                    {
                        "operator": "contains",
                        "path": [
                            "title"
                        ],
                        "value": "ai"
                    }
                ]
            }
        ]
    },
```

Pagination is also enabled for this functionality, and the default number of returned results is 50 with no entries skipped. Use the following paramteres to get the desired page:`

- `skip`
- `take`

Here is an example of retrieving the first 3 content infos that contain the value `uniquepathid://scope_abcdibgznc4bkdcx120zm5d` in the `folderIdPath` metadata and the value `ai` for the `title` metadata.

```python
content_info_result = unique_sdk.Content.get_info(
    user_id=user_id,
    company_id=company_id,
    metadataFilter={
        "or": [
            {
                "and": [
                    {
                        "operator": "contains",
                        "path": [
                            "folderIdPath"
                        ],
                        "value": "uniquepathid://scope_abcdibgznc4bkdcx120zm5d"
                    },
                    {
                        "operator": "contains",
                        "path": [
                            "title"
                        ],
                        "value": "ai"
                    }
                ]
            }
        ]
    },
    skip=0,
    take=3,
)
```

#### `unique_sdk.Content.get_infos`

Allows you to get content infos. To filter the results you can define a either metadata filter in UniqueQL language or specify a parentId. If both are defined, the function will throw an error.

I f you want to learn more about UniqueQL, you can find out more about it in the [UniqueQL](#uniqueql) section. An example of a metadata filter defined with UniqueQL is the following:

```python
    metadataFilter: {
        "or": [
            {
                "and": [
                    {
                        "operator": "contains",
                        "path": [
                            "folderIdPath"
                        ],
                        "value": "uniquepathid://test_id"
                    },
                    {
                        "operator": "contains",
                        "path": [
                            "title"
                        ],
                        "value": "ai"
                    }
                ]
            }
        ]
    },
```

Pagination is also enabled for this functionality, and the default number of returned results is 50 with no entries skipped. Use the following paramteres to get the desired page:`

- `skip`
- `take`

Here is an example of retrieving the first 3 content infos that contain the value `uniquepathid://scope_abcdibgznc4bkdcx120zm5d` in the `folderIdPath` metadata and the value `ai` for the `title` metadata.

```python
content_info_result = unique_sdk.Content.get_infos(
    user_id=user_id,
    company_id=company_id,
    metadataFilter={
        "or": [
            {
                "and": [
                    {
                        "operator": "contains",
                        "path": [
                            "folderIdPath"
                        ],
                        "value": "uniquepathid://scope_abcdibgznc4bkdcx120zm5d"
                    },
                    {
                        "operator": "contains",
                        "path": [
                            "title"
                        ],
                        "value": "ai"
                    }
                ]
            }
        ]
    },
    skip=0,
    take=3,
)
```

Here is an example of retrieving the contents based on a parentId.

```python
content_info_result = unique_sdk.Content.get_infos(
    user_id=user_id,
    company_id=company_id,
    parentId="scope_ahefgj389srjbfejkkk98u"
)
```

#### `unique_sdk.Content.upsert`

Enables upload of a new Content into the Knowledge base of unique into a specific scope with `scopeId` or a specific `chatId`. One of the two must be set.

Typical usage is the following. That creates a Content and uploads a file

```python

createdContent = upload_file(
    userId,
    companyId,
    "/path/to/file.pdf",
    "test.pdf",
    "application/pdf",
    "scope_stcj2osgbl722m22jayidx0n",
    ingestionConfig={
        "chunkMaxTokens": 1000,
        "chunkStrategy": "default",
        "uniqueIngestionMode": "standard",
    },
    metadata={
        "folderIdPath": "uniquepathid://scope_id"
    }
)

def upload_file(
    userId,
    companyId,
    path_to_file,
    displayed_filename,
    mimeType,
    scope_or_unique_path,
    ingestion_config=None,
    metadata=None,
):
    size = os.path.getsize(path_to_file)
    createdContent = unique_sdk.Content.upsert(
        user_id=userId,
        company_id=companyId,
        input={
            "key": displayed_filename,
            "title": displayed_filename,
            "mimeType": mimeType,
            "ingestionConfig": ingestionConfig,
            "metadata": metadata,
        },
        scopeId=scope_or_unique_path,
    )

    uploadUrl = createdContent.writeUrl

    # upload to azure blob storage SAS url uploadUrl the pdf file translatedFile make sure it is treated as a application/pdf
    with open(path_to_file, "rb") as file:
        requests.put(
            uploadUrl,
            data=file,
            headers={
                "X-Ms-Blob-Content-Type": mimeType,
                "X-Ms-Blob-Type": "BlockBlob",
            },
        )

    unique_sdk.Content.upsert(
        user_id=userId,
        company_id=companyId,
        input={
            "key": displayed_filename,
            "title": displayed_filename,
            "mimeType": mimeType,
            "byteSize": size,
            "ingestionConfig": ingestionConfig,
            "metadata": metadata,
        },
        scopeId=scope_or_unique_path,
        readUrl=createdContent.readUrl,
    )

    return createdContent

```

#### `unique_sdk.Content.ingest_magic_table_sheets`

Allows you to ingest a magic table sheet, each row is processed and converted into a content.
```python
    params = {
      "user_id": user_id,
      "company_id": company_id,
      "data": [
         {
            "rowId": "2",
            "columns": [
               {"columnId": "0", "columnName": "Section", "content": "Other"},
               {"columnId": "1", "columnName": "Question", "content": "What do you know?"},
               {
                  "columnId": "2",
                  "columnName": "Knowledge Base Answer",
                  "content": "Lorem Ipsum is simply dummy texktop publishing software.",
               },
            ],
         },
      ],
      "ingestionConfiguration": {
         "columnIdsInMetadata": ["1", "2"],
         "columnIdsInChunkText": ["1", "2"],
      },
      "metadata": {
         "libraryName": "foo",
      },
      "scopeId": scope_id,
      "sheetName": "Sheet1",
   }

    unique_sdk.Content.ingest_magic_table_sheets(**params)
```

### Message

#### `unique_sdk.Message.list`

Retrieve a list of messages for a provided `chatId`.

```python
messages = unique_sdk.Message.list(
    user_id=user_id,
    company_id=company_id,
    chatId=chat_id,
)
```

#### `unique_sdk.Message.retrieve`

Get a single chat message.

```python
message = unique_sdk.Message.retrieve(
    user_id=user_id,
    company_id=company_id,
    id=message_id,
    chatId=chat_id,
)
```

#### `unique_sdk.Message.create`

Create a new message in a chat.

```python
message = unique_sdk.Message.create(
    user_id=user_id,
    company_id=company_id,
    chatId=chat_id,
    assistantId=assistant_id,
    text="Hello.",
    role="ASSISTANT",
)
```

#### `unique_sdk.Message.modify`

Modify an existing chat message.

ℹ️ if you modify the debugInfo only do it on the user message as this is the only place that is displayed in the frontend.

```python
message = unique_sdk.Message.modify(
    user_id=user_id,
    company_id=company_id,
    id=message_id,
    chatId=chat_id,
    text="Updated message text"
)
```

#### `unique_sdk.Message.delete`

Delete a chat message.

```python
message = unique_sdk.Message.delete(
    message_id,
    user_id=user_id,
    company_id=company_id,
    chatId=chat_id,
)
```

#### `unique_sdk.Integrated.stream`

Streams the answer to the chat frontend. Given the messages.

if the stream creates [source0] it is referenced with the references from the search context.

E.g.

```
Hello this information is from [srouce1]
```

adds the reference at index 1 and then changes the text to:

```
Hello this information is from <sub>0</sub>
```

```python
unique_sdk.Integrated.chat_stream_completion(
    user_id=userId,
    company_id=companyId,
    assistantMessageId=assistantMessageId,
    userMessageId=userMessageId,
    messages=[
        {
            "role": "system",
            "content": "be friendly and helpful"
        },
        {
            "role": "user",
            "content": "hello"
        }
    ],
    chatId=chatId,

    searchContext=  [
        {
            "id": "ref_qavsg0dcl5cbfwm1fvgogrvo",
            "chunkId": "0",
            "key": "some reference.pdf : 8,9,10,11",
            "sequenceNumber": 1,
            "url": "unique://content/cont_p8n339trfsf99oc9f36rn4wf"
        }
    ],  # optional
    debugInfo={
        "hello": "test"
    }, # optional
    startText= "I want to tell you about: ", # optional
    model= "AZURE_GPT_4_32K_0613", # optional
    timeout=8000,  # optional in ms
    options={
                "temperature": 0.5
            } # optional
)
```

**Warning:** Currently, the deletion of a chat message does not automatically sync with the user UI. Users must refresh the chat page to view the updated state. This issue will be addressed in a future update of our API.


#### `unique_sdk.Integrated.responses_stream`

Streams the answer to the chat frontend using the Responses API. Given the messages.

if the stream creates [source0] it is referenced with the references from the search context.

E.g.

```
Hello this information is from [source1]
```

adds the reference at index 1 and then changes the text to:

```
Hello this information is from <sub>0</sub>
```

```python
unique_sdk.Integrated.responses_stream(
    user_id=userId,
    company_id=companyId,
    model="AZURE_o3_2025_0416",
    assistantMessageId=assistantMessageId,
    userMessageId=userMessageId,
    input="Tell me about the curious case of neural text degeneration",
    chatId=chatId,
)
```

**Warning:** Currently, the deletion of a chat message does not automatically sync with the user UI. Users must refresh the chat page to view the updated state. This issue will be addressed in a future update of our API.

### Chat Completion

#### `unique_sdk.ChatCompletion.create`

Send a prompt to an AI model supported by Unique FinanceGPT and receive a result. The `messages` attribute must follow the [OpenAI API format](https://platform.openai.com/docs/api-reference/chat).

```python
chat_completion = unique_sdk.ChatCompletion.create(
    company_id=company_id,
    user_id=user_id
    model="AZURE_GPT_35_TURBO",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ],
    options={
            "temperature": 0.5
        } # optional
)
```

### Embeddings

#### `unique_sdk.Embeddings.create`

Sends an array of `text` to the AI model for embedding. And retrieve a vector of embeddings.

```python
result = unique_sdk.Embeddings.create(
    user_id=user_id,
    company_id=company_id,
    texts=["hello", "hello"],
)
print(result.embeddings[0][0])
```

### Acronyms

#### `unique_sdk.Acronyms.get`

Fetches the acronyms defined on the company. Often used to replace in user prompts, so the acronym is resolved to give better guidance to the LLM during completion.

```python
result = unique_sdk.Acronyms.get(
    user_id=user_id,
    company_id=company_id,
)
print(result)
```

### Search

#### `unique_sdk.Search.create`

Search the Unique FinanceGPT Knowledge database for RAG (Retrieval-Augmented Generation). The API supports vector search and a `searchType` that combines vector and full-text search, enhancing the precision of search results.

These are the options are available for `searchType`:

- `VECTOR`
- `COMBINED`

`limit` (max 1000) and `page` are optional for iterating over results.
`chatOnly` Restricts the search exclusively to documents uploaded within the chat.
`scopeIds` Specifies a collection of scope IDs to confine the search.
`language` Optional. The language specification for full text search.
`reranker` Optional. The reranker service to be used for re-ranking the search results.
`chatId` Optional, adds the documents uploaded in this chat to the scope of searched documents.
`scoreThreshold` Optional, sets the minimum similarity score for search results to be considered. Using 0 is recommended.

```python
search = unique_sdk.Search.create(
    user_id=user_id,
    company_id=company_id,
    chatId=chat_id
    searchString="What is the meaning of life, the universe and everything?",
    searchType="VECTOR",
    chatOnly=false,
    scopeIds=["scope_..."],
    language="German",
    reranker={"deploymentName": "my_deployment"},
    limit=20,
    page=1
    scoreThreshold=0
)
```

### Search String

#### `unique_sdk.SearchString.create`

User messages are sometimes suboptimal as input prompts for vector or full-text knowledge base searches. This is particularly true as a conversation progresses and a user question may lack crucial context for a successful search.

This API transforms and translates (into English) the user's message into an ideal search string for use in the [Search.create](#unique_sdksearchcreate) API method.

Adding a `chatId` or `messages` as arguments allows the message history to provide additional context to the search string. For example, "Who is the author?" will be expanded to "Who is the author of the book 'The Hitchhiker's Guide to the Galaxy'?" if previous messages referenced the book.

```python
search_string = unique_sdk.SearchString.create(
    user_id=user_id,
    company_id=company_id,
    prompt="Was ist der Sinn des Lebens, des Universums und des ganzen Rests?",
    chat_id=chat_id
)
```

### Short Term Memory

For saving data in between chats there is the Short Term Memory functionality to save small data in between rounds of chat e.g. language, search results and so on.
For this 10k chars can be used. You can save a short term memory for a chat `chatId` or for a message `messageId`.
you need to provide an `memoryName` as an identifier.

you can then save it and retreive it live defined below.


#### `unique_sdk.ShortTermMemory.create`

```python
c = unique_sdk.ShortTermMemory.create(
    user_id=user_id,
    company_id=company_id,
    data="hello",
    chatId="chat_x0xxtj89f7drjp4vmued3q",
    # messageId = "msg_id",
    memoryName="your memory name",
)
print(c)
```

#### `unique_sdk.ShortTermMemory.find-latest`

```python
m = unique_sdk.ShortTermMemory.find_latest(
    user_id=user_id,
    company_id=company_id,
    chatId="chat_x0xxtj89f7drjp4vmued3q",
     # messageId = "msg_id",
    memoryName="your memory name",
)
print(m)
```

### Message Assessment

Used to create and modify message assessments for tracking hallucinations and compliance evaluations of assistant messages.

#### `unique_sdk.MessageAssessment.create`

Create a new message assessment for an assistant message.

```python
assessment = unique_sdk.MessageAssessment.create(
    user_id=user_id,
    company_id=company_id,
    assistant_message_id="msg_...",
    status="DONE",
    explanation="This response contains incorrect information about...",
    label="RED",
    type="HALLUCINATION",
    title="Hallucination detected",
    isVisible=True
)
```

#### `unique_sdk.MessageAssessment.modify` 

Modify an existing message assessment.

```python
assessment = unique_sdk.MessageAssessment.modify(
    user_id=user_id,
    company_id=company_id,
    assistant_message_id="msg_...",
    status="DONE",
    explanation="Updated explanation...",
    label="RED",
    title="update title"
    type="HALLUCINATION"
)
```

### Folder

#### `unique_sdk.Folder.get_info`

Get a folder by scope id or by path.

By scope id:

```python
unique_sdk.Folder.get_info(
   user_id=user_id,
   company_id=company_id,
   scopeId="scope_w78wfn114va9o22s13r03yq",
)
```

By path:

```python
unique_sdk.Folder.get_info(
   user_id=user_id,
   company_id=company_id,
   folderPath="/Company/Atlas/Due Dilligence/Arch,
)
```

#### `unique_sdl.Folder.get_infos`

Get paginated folders info based on parentId. If the parentId is not defined, the root folders will be returned.

```python
unique_sdk.Folder.get_infos(
    user_id=user_id,
    company_id=company_id,
    take=10,                                    #optional
    skip=5,                                     #optional
    parentId="scope_s18seqpnltf35niydg77xgyp"   #optional
)
```

#### `unique_sdk.Folder.create_paths`

Create each folder in the provided list of paths if it does not already exist.

```python
unique_sdk.Folder.create_paths(
   user_id=user_id,
   company_id=company_id,
   paths=["/unique/path1", "/unique/path2"],
)
```

#### `unique_sdk.Folder.update_ingestion_config`

Allows you to update the ingestion config of a folder and choose whether to apply to the subscopes or not: `

- `ingestionConfig`
- `applyToSubScopes`

The update can be done by referencing the folder by id or by path. If none of them are provided. the API will return an error. If both of them are provided, the scope id will take precedence.

Example of updating the ingestion config of a folder and its subfolders using the id.

```python
unique_sdk.Folder.update_ingestion_config(
    user_id=user_id,
    company_id=company_id,
    scopeId="scope_qbnkde820dbmuw2900,
    ingestionConfig={
        "chunkStrategy": "default",
        "uniqueIngestionMode": "standard",
    },
    applyToSubScopes=True
)
```

Example of updating the ingestion config of a folder and its subfolders using the path.

```python
unique_sdk.Folder.update_ingestion_config(
    user_id=user_id,
    company_id=company_id,
    folderPath="/Company/folder1/folder2",
    ingestionConfig={
        "chunkStrategy": "default",
        "uniqueIngestionMode": "standard",
    },
    applyToSubScopes=True
)
```

#### `unique_sdk.Folder.add_access`

Allows you to add access to a folder and apply to the subfolders or not: `

- `scopeAccesses`
- `applyToSubScopes`

The update can be done by referencing the folder by id or by path. If none of them are provided. the API will return an error. If both of them are provided, the scope id will take precedence.

Example of adding access to a folder and its subfolders using the id.

```python
unique_sdk.Folder.add_access(
    user_id=user_id,
    company_id=company_id,
    scopeId="scope_231e4kjn4foffww34",
    scopeAccesses=[
        {
            "entityId": "group_id",
            "type": "WRITE",
            "entityType": "GROUP",
        }
    ],
    applyToSubScopes=True,
)
```

Example of adding access to a folder and its subfolders using the folder path.

```python
unique_sdk.Folder.add_access(
    user_id=user_id,
    company_id=company_id,
    folderPath="/Company/folder1/folder2"
    scopeAccesses=[
        {
            "entityId": "group_id",
            "type": "WRITE",
            "entityType": "GROUP",
        }
    ],
    applyToSubScopes=True,
)
```

#### `unique_sdk.Folder.remove_access`

Allows you to delete access from a folder and apply to the subfolders or not:

- `scopeAccesses`
- `applyToSubScopes`

The update can be done by referencing the folder by id or by path. If none of them are provided. the API will return an error. If both of them are provided, the scope id will take precedence.


Example of deleting the access from a folder and its subfolders using the id.

```python
unique_sdk.Folder.remove_access(
    user_id=user_id,
    company_id=company_id,
    scopeId="scope_dwekjnf3330woioppm,
    scopeAccesses=[
        {
            "entityId": "group_id",
            "type": "WRITE",
            "entityType": "GROUP",
        }
    ],
    applyToSubScopes=True,
)
```


Example of deleting the access from a folder and its subfolders using the path.

```python
unique_sdk.Folder.remove_access(
    user_id=user_id,
    company_id=company_id,
    folderPath="/Company/folder1/folder2"
    scopeAccesses=[
        {
            "entityId": "group_id",
            "type": "WRITE",
            "entityType": "GROUP",
        }
    ],
    applyToSubScopes=True,
)
```

### Space

#### `unique_sdk.Space.delete_chat`

Delete a space chat by id. If the chat does not exist, the function will return an error.

```python
unique_sdk.Space.delete_chat(
    user_id=user_id,
    company_id=company_id,
    chat_id="chat_dejfhe729br398",
)
```

## UniqueQL

[UniqueQL](https://unique-ch.atlassian.net/wiki/x/coAXHQ) is an advanced query language designed to enhance search capabilities within various search modes such as Vector, Full-Text Search (FTS), and Combined. This query language enables users to perform detailed searches by filtering through metadata attributes like filenames, URLs, dates, and more. UniqueQL is versatile and can be translated into different query formats for various database systems, including PostgreSQL and Qdrant.

### UniqueQL Query Structure

A UniqueQL query is composed of a path, an operator, and a value. The path specifies the metadata attribute to be filtered, the operator defines the type of comparison, and the value provides the criteria for the filter.

A metadata filter can be designed with UniqueQL's `UQLOperator` and `UQLCombinator` as follows:

```python
metadata_filter = {
        "path": ['diet', '*'],
        "operator": UQLOperator.NESTED,
        "value": {
            UQLCombinator.OR : [
                {
                    UQLCombinator.OR: [
                        {
                            "path": ['food'],
                            "operator": UQLOperator.EQUALS,
                            "value": "meat",
                        },
                        {
                            "path": ['food'],
                            "operator": UQLOperator.EQUALS,
                            "value": 'vegis',
                        },
                    ],
                },
                {
                    "path": ['likes'],
                    "operator": UQLOperator.EQUALS,
                    "value": true,
                },
            ],
        },
    }
```

### Metadata Filtering

A metadata filter such as the one designed above can be used in a `Search.create` call by passing it the `metaDataFilter` parameter.

```python
    search_results = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        searchString=search_string,
        searchType="COMBINED",
        # limit=2,
        metaDataFilter=metadata_filter,
    )
```

## Utils

- [Chat History](#chat-history)
- [File Io](#file-io)
- [Sources](#sources)
- [token](#token)
- [Chat In Space](#chat-in-space)

### Chat History

#### `unique_sdk.utils.chat_history.load_history`

A helper function that makes sure the chat history is fully loaded and cut to the size of the token window that it fits into the next round of chat interactions.

- `maxTokens` max tokens of the model used
- `percentOfMaxTokens`=0.15 % max history in % of `maxTokens`
- `maxMessages`=4, maximal number of messages included in the history.

this method also directly returns a correct formatted history that can be used in the next chat round.

```python
history = unique_sdk.utils.chat_history.load_history(
    userId,
    companyId,
    chatId
)
```

#### `unique_sdk.utils.chat_history.convert_chat_history_to_injectable_string`

convert history into a string that can be injected into a prompt. it als returns the token length of the converted history.

```
chat_history-string, chat_context_token_length = unique_sdk.utils.chat_history.convert_chat_history_to_injectable_string(
    history
)
```

### File Io

Interacting with the knowledge-base.

#### `unique_sdk.utils.file_io.download_content`

download files and save them into a folder in `/tmp`

for example using the readUrl from a content.

```python
pdfFile = download_content(
    companyId=companyId,
    userId=userId,
    content_id="cont_12412",
    filename="hello.pdf",
    chat_id=None # If specified, it downloads it from the chat
)
```

#### `unique_sdk.utils.file_io.upload_file`

Allows for uploading files that then get ingested in a scope or a chat.

```python
createdContent = upload_file(
    companyId=companyId,
    userId=userId,
    path_to_file="/tmp/hello.pdf",
    displayed_filename="hello.pdf",
    mime_type="application/pdf",
    scope_or_unique_path="scope_stcj2osgbl722m22jayidx0n",
    chat_id=None,
)
```

### Sources

#### `unique_sdk.utils.sources.merge_sources`

Merges multiple search results based on their 'id', removing redundant document and info markers.

This function groups search results by their 'id' and then concatenates their texts,
cleaning up any document or info markers in subsequent chunks beyond the first one.

Parameters:

- searchContext (list): A list of dictionaries, each representing a search result with 'id' and 'text' keys.

Returns:

- list: A list of dictionaries with merged texts for each unique 'id'.

`searchContext` is an list of search objects that are returned by the search.

```python
search = unique_sdk.Search.create(
    user_id=userId,
    company_id=companyId,
    chatId=chatId,
    searchString="Who is Harry P?",
    searchType="COMBINED",
    scopeIds="scope_dsf...",
    limit=30,
    chatOnly=False,
)

searchContext = unique_sdk.utils.token.pick_search_results_for_token_window(
        search["data"], config["maxTokens"] - historyLength
    )

searchContext = unique_sdk.utils.sources.merge_sources(search)

```

#### `unique_sdk.utils.sources.sort_sources`

Sort sources by order of appearance in documents

```python

search = unique_sdk.Search.create(
    user_id=userId,
    company_id=companyId,
    chatId=chatId,
    searchString="Who is Harry P?",
    searchType="COMBINED",
    scopeIds="scope_dsf...",
    limit=30,
    chatOnly=False,
)

searchContext = unique_sdk.utils.token.pick_search_results_for_token_window(
        search["data"], config["maxTokens"] - historyLength
    )

searchContext = unique_sdk.utils.sources.sort_sources(search)
```

#### `unique_sdk.utils.sources.post_process_sources`

Post-processes the provided text by converting source references into superscript numerals (required
format by backend to display sources in the chat window)

This function searches the input text for patterns that represent source references (e.g., [source1])
and replaces them with superscript tags, incrementing the number by one.

Parameters:

- text (str): The text to be post-processed.

Returns:

- str: The text with source references replaced by superscript numerals.

Examples:

- postprocessSources("This is a reference [source0]") will return "This is a reference <sup>1</sup>".

```python

text_with_sup = post_process_sources(text)
```

### Token

#### unique_sdk.utils.token.pick_search_results_for_token_window

Selects and returns a list of search results that fit within a specified token limit.

This function iterates over a list of search results, each with a 'text' field, and
encodes the text using a predefined encoding scheme. It accumulates search results
until the token limit is reached or exceeded.

Parameters:

- searchResults (list): A list of dictionaries, each containing a 'text' key with string value.
- tokenLimit (int): The maximum number of tokens to include in the output.

Returns:

- list: A list of dictionaries representing the search results that fit within the token limit.

```python
search = unique_sdk.Search.create(
    user_id=userId,
    company_id=companyId,
    chatId=chatId,
    searchString="Who is Harry P?",
    searchType="COMBINED",
    scopeIds="scope_dsf...",
    limit=30,
    chatOnly=False,
)

searchContext = unique_sdk.utils.token.pick_search_results_for_token_window(
        search["data"], config["maxTokens"] - historyLength
    )
```

#### unique_sdk.utils.token.count_tokens

Counts the number of tokens in the provided text.

This function encodes the input text using a predefined encoding scheme
and returns the number of tokens in the encoded text.

Parameters:

- text (str): The text to count tokens for.

Returns:

- int: The number of tokens in the text.

```python
hello = "hello you!"
searchContext = unique_sdk.utils.token.count_tokens(hello)
```

### Chat In Space

#### `unique_sdk.utils.chat_in_space.send_message_and_wait_for_completion`

The following script enables you to chat within a space using an assistant. You must provide an `assistantId` (e.g., `assistant_hjcdga64bkcjnhu4`) and the message `text` to initiate the conversation. You can send the message in an existing chat by specifying a `chat_id`, or omit the `chat_id` to automatically create a new chat session. Check the optional parameteres list for more configs.

The script sends a prompt asynchronously and continuously polls for completion, which is determined when the `stoppedStreamingAt` field of the message becomes non-null.

**Optional parameters:**
- `tool_choices`: A list of tool names to be used for the message (e.g., `["WebSearch"]`). If not provided, no tools will be used. The tools supported right now are `WebSearch` and `InternalSearch`.
- `scope_rules`: A filter to specify the scope rules for the message, allowing you to restrict the context or data sources available to the assistant. The filter is written in UniqueQL language. Find out more about the language in the UniqueQL section.
- `chat_id`: The ID of the chat where the message should be sent. If omitted, a new chat will be created.
- `poll_interval`: The number of seconds to wait between polling attempts (default: `1` second).
- `max_wait`: The maximum number of seconds to wait for the message to complete (default: `60` seconds).

The script ensures you can flexibly interact with spaces in new or ongoing chats, with fine-grained control over tools, context, and polling behavior.

```python
latest_message = await unique_sdk.utils.chat_in_space.send_message_and_wait_for_completion(
    user_id=user_id,
    company_id=company_id,
    assistant_id=assistant_id,
    text="Tell me a short story.",
    chat_id=chat_id,                # Optional - if no chat id is specified, a new chat will be created
    tool_choices=["WebSearch"],
    scope_rules={
        "or": [
            {
                "operator": "in",
                "path": [
                    "contentId"
                ],
                "value": [
                    "cont_u888z7cazxxm4lugfdjq7pks"
                ]
            },
            {
                "operator": "contains",
                "path": [
                    "folderIdPath"
                ],
                "value": "uniquepathid://scope_btfo28b3eeelwh5obwgea71bl/scope_fn56ta67knd6w4medgq3028fx"
            }
        ]
    },
)
```

#### `unique_sdk.utils.chat_in_space.chat_against_file`

The following script enables you to chat against a file.

You must provide the following parameters:
- `assistantId`: The assistant to be used for the chat.
- `path_to_file`: The local path of the file to be uploaded.
- `displayed_filename`: The name of the file to be displayed.
- `mime_type`: The mime type of the ifle to be uploaded.
- `text`: The text to be sent to the chat for chatting against the file.

The script creates a chat and uploads the file to it. It then keeps polling the `ingestionState` field of the message, waiting for it to reach `FINISHED`, signaling the upload is complete. Once the file uploads successfully, the script sends the text, continues polling for completion, and finally retrieves the response message.

**Optional parameters:**
- `poll_interval`: The number of seconds to wait between polling attempts (default: `1` second).
- `max_wait`: The maximum number of seconds to wait for the message to complete (default: `60` seconds).

Example of chatting against a PDF. (The usage can be extended to any supported file type)

```python
latest_message = await unique_sdk.utils.chat_in_space.chat_against_file(
    user_id=user_id,
    company_id=company_id,
    assistant_id="assistant_hjcdga64bkcjnhu4",
    path_to_file="/files/hello.pdf",
    displayed_filename="hello.pdf"
    mime_type="application/pdf"
    text="Give me a bullet point summary of the file.",
)
```

## Error Handling

## Examples

An example Flask app demonstrating the usage of each API resource and how to interact with Webhooks is available in our repository at `/examples/custom-assistant`.

## Credits

This is a _fork_ / inspired-by the fantastic Stripe Python SDK (https://github.com/stripe/stripe-python).
