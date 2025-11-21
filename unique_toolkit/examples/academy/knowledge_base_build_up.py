# %%

import logging
from pathlib import Path, PurePath
from typing import Any

from unique_toolkit import (
    KnowledgeBaseService,
)
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import ContentChunk, ContentSearchType
from unique_toolkit.content.smart_rules import AndStatement, Operator, Statement
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
from unique_toolkit.language_model import LanguageModelName

# %%

# Define the local root folder path and the root folder scope id
# --------------------------------------------------------------

local_root_folder_path = Path(__file__).parent / "data"

root_folder_scope_id = (
    "scope_l9w7jsv190bp7sip4r2wuab0"  # Scope to upload the local folder to
)
root_folder_path = PurePath("/Company/Cedric")  # Path to the local folder

settings = UniqueSettings.from_env_auto_with_sdk_init()
kb_service = KnowledgeBaseService.from_settings(settings=settings)

_LOGGER = logging.getLogger(__name__)

# %%

# Upload the local folder and subfolders to the knowledge base
# --------------------------------------------------------------

folders_to_create_paths = [
    root_folder_path / folder.relative_to(local_root_folder_path)
    for folder in local_root_folder_path.rglob("*")
    if folder.is_dir()
]

files_to_upload = [
    (
        root_folder_path / local_file_path.relative_to(local_root_folder_path),
        local_file_path,
    )
    for local_file_path in local_root_folder_path.rglob("*")
    if local_file_path.is_file()
]


def hr_metadata_generator(
    local_file_path: Path, remote_folder_path: PurePath
) -> dict[str, Any]:
    return {"country": remote_folder_path.name, "departement": "HR"}


kb_service.batch_file_upload(
    local_files=[local_file_path for _, local_file_path in files_to_upload],
    remote_folders=[remote_file_path.parent for remote_file_path, _ in files_to_upload],
    overwrite=True,
    metadata_generator=hr_metadata_generator,
)

# %%

# Smart rule definition
# --------------------------------------------------------------

country = "India"
smart_rule_departement = Statement(
    operator=Operator.EQUALS, value="HR", path=["departement"]
)
smart_rule_country = Statement(
    operator=Operator.EQUALS, value=country, path=["country"]
)
smart_rule = AndStatement(and_list=[smart_rule_departement, smart_rule_country])


# Test the smart rule
infos = kb_service.get_paginated_content_infos(
    metadata_filter=smart_rule.model_dump(mode="json")
)

for info in infos.content_infos:
    print(info.title)


# %%

# User interaction with the knowledge base
# --------------------------------------------------------------

user_query = "I am becoming a mother in 2 months, what are my rights"

content_chunks = kb_service.search_content_chunks(
    search_string=user_query,
    search_type=ContentSearchType.COMBINED,
    limit=10,
    score_threshold=0.7,
    metadata_filter=smart_rule.model_dump(mode="json"),
)


for content_chunk in content_chunks:
    print(content_chunk.title)

# %%

# Generate a response to the user query
# --------------------------------------------------------------


def content_chunks_to_string(content_chunks: list[ContentChunk]) -> str:
    header = "| Source Tag | Title |  URL | Text \n" + "| --- | --- | --- | --- |\n"
    rows = [
        f"| [source{index}] | {chunk.title} | {chunk.url} | {chunk.text} \n"
        for index, chunk in enumerate(content_chunks)
    ]
    return header + "\n".join(rows)


client = get_openai_client(unique_settings=settings)

builder = (
    OpenAIMessageBuilder()
    .system_message_append(
        content="You act as a HR assistant for our employees.\n"
        "You are given a user query and you need to answer it based on the knowledge base.\n"
    )
    .developper_message_append(
        content=f"The system retrieved the following content chunks: {content_chunks_to_string(content_chunks)}"
    )
    .user_message_append(content=user_query)
)

response = client.chat.completions.create(
    messages=builder.messages,
    model=LanguageModelName.AZURE_GPT_4o_2024_1120,
)

print(response.choices[0].message.content)

# %%
