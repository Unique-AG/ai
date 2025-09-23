# %%
from unique_toolkit import (
    ChatService,
    LanguageModelName,
)
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import (
    ContentChunk,
)
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)

settings = UniqueSettings.from_env_auto_with_sdk_init()
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    chat_service = ChatService(event)
    chunks = [
        ContentChunk(
            text="Unique is a company that provides the platform for AI-powered solutions.",
            order=0,
            chunk_id="chunk_id_0",
            key="key_0",
            title="title_0",
            start_page=1,
            end_page=1,
            url="https://www.unique.ai",
            id="id_0",
        ),
        ContentChunk(
            text="Unique is your Responsible AI Partner, with extensive experience in implementing AI solutions for enterprise clients in financial services.",
            order=1,
            chunk_id="chunk_id_1",
            key="key_1",
            title="title_1",
            start_page=1,
            end_page=1,
            url="https://www.unique.ai",
            id="id_1",
        ),
    ]

    def to_source_table(chunks: list[ContentChunk]) -> str:
        header = "| Source Number | Title |  URL | \n" + "| --- | --- | --- | --- |\n"
        rows = [
            f"| {index} | {chunk.title} | {chunk.url} |\n"
            for index, chunk in enumerate(chunks)
        ]
        return header + "\n".join(rows)

    reference_guidelines = """
    Whenever you use information retrieved with a tool, you must adhere to strict reference guidelines. 
    You must strictly reference each fact used with the `source_number` of the corresponding passage, in 
    the following format: '[source<order_number>]'.

    Example:
    - The stock price of Apple Inc. is $150 [source0] and the company's revenue increased by 10% [source1].
    - Moreover, the company's market capitalization is $2 trillion [source2][source3].
    - Our internal documents tell us to invest[source4] (Internal)
    """
    messages = (
        OpenAIMessageBuilder()
        .system_message_append(
            content=f"You are a helpful assistant. {reference_guidelines}"
        )
        .user_message_append(
            content=f"<Sources> {to_source_table(chunks)}</Srouces>\n\n User question: {event.payload.user_message.text}"
        )
        .messages
    )

    chat_service.complete_with_references(
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4o_2024_1120,
        content_chunks=chunks,
    )
