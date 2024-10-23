from datetime import datetime

from unique_toolkit.app.schemas import Event
from unique_toolkit.content.schemas import ContentChunk, ContentMetadata
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelTool,
    LanguageModelToolParameterProperty,
    LanguageModelToolParameters,
    LanguageModelUserMessage,
)
from unique_toolkit.language_model.service import LanguageModelService

# Sample tool for testing
weather_tool = LanguageModelTool(
    name="get_weather",
    description="Get the current weather for a location",
    parameters=LanguageModelToolParameters(
        type="object",
        properties={
            "location": LanguageModelToolParameterProperty(
                type="string", description="The city and state, e.g. San Francisco, CA"
            ),
            "unit": LanguageModelToolParameterProperty(
                type="string",
                description="The unit system to use. Either 'celsius' or 'fahrenheit'.",
                enum=["celsius", "fahrenheit"],
            ),
        },
        required=["location"],
    ),
)


@pytest.mark.usefixtures("event")
class TestLanguageModelServiceIntegration:
    @pytest.fixture(autouse=True)
    def setup(self, event: Event):
        self.event = event
        self.service = LanguageModelService(self.event)
        self.test_messages = LanguageModelMessages(
            [
                LanguageModelSystemMessage(content="You are Shakespeare"),
                LanguageModelUserMessage(content="Tell a joke"),
            ]
        )
        self.model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106

    def test_can_complete(self):
        response = self.service.complete(
            messages=self.test_messages,
            model_name=self.model_name,
        )
        assert len(response.choices) == 1

        choice = response.choices[0]
        assert isinstance(choice.message.content, str)

    def test_can_stream_complete(self):
        response = self.service.stream_complete(
            messages=self.test_messages,
            model_name=self.model_name,
        )
        assert response is not None
        assert isinstance(response.message.text, str)

    def test_can_stream_complete_with_search_context(self):
        content_chunks = [
            ContentChunk(
                id="cont_n9orqit7zb2mwa62kuqzok2s",
                text="some text",
                key="white-paper-odi-2018-dec-08.pdf : 3,4,9,10",
                chunk_id="chunk_g5kxvtxssofj33k453u3f8fe",
                url=None,
                title=None,
                order=2,
                start_page=3,
                end_page=10,
                object="search.search",
                metadata=ContentMetadata(
                    key="white-paper-odi-2018-dec-08.pdf", mime_type="application/pdf"
                ),
                internally_stored_at=datetime(2024, 7, 22, 11, 51, 40, 693000),
                created_at=datetime(2024, 7, 22, 11, 51, 39, 392000),
                updated_at=datetime(2024, 7, 22, 11, 57, 3, 446000),
            )
        ]
        response = self.service.stream_complete(
            messages=self.test_messages,
            model_name=self.model_name,
            content_chunks=content_chunks,
        )
        assert response is not None
        assert isinstance(response.message.text, str)

    def test_complete_with_tool(self):
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.USER,
                    content="What's the weather in New York?",
                )
            ]
        )

        response = self.service.complete(
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_4_0613,
            tools=[weather_tool],
        )

        assert response.choices[0].message.tool_calls is not None
        assert response.choices[0].message.tool_calls[0].function.name == "get_weather"

    def test_stream_complete_with_tool(self):
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.USER,
                    content="What's the weather in New York?",
                )
            ]
        )

        response = self.service.stream_complete(
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_4_0613,
            tools=[weather_tool],
        )

        assert response.tool_calls is not None
        assert response.tool_calls[0].name == "get_weather"

    @pytest.mark.asyncio
    async def test_can_complete_async(self):
        response = await self.service.complete_async(
            messages=self.test_messages,
            model_name=self.model_name,
        )
        assert len(response.choices) == 1

        choice = response.choices[0]
        assert isinstance(choice.message.content, str)

    @pytest.mark.asyncio
    async def test_can_stream_complete_async(self):
        response = await self.service.stream_complete_async(
            messages=self.test_messages,
            model_name=self.model_name,
        )

        assert response is not None
        assert isinstance(response.message.text, str)

    @pytest.mark.asyncio
    async def test_can_stream_complete_with_search_context_async(self):
        content_chunks = [
            ContentChunk(
                id="cont_n9orqit7zb2mwa62kuqzok2s",
                text="some text",
                key="white-paper-odi-2018-dec-08.pdf : 3,4,9,10",
                chunk_id="chunk_g5kxvtxssofj33k453u3f8fe",
                url=None,
                title=None,
                order=2,
                start_page=3,
                end_page=10,
                object="search.search",
                metadata=ContentMetadata(
                    key="white-paper-odi-2018-dec-08.pdf", mime_type="application/pdf"
                ),
                internally_stored_at=datetime(2024, 7, 22, 11, 51, 40, 693000),
                created_at=datetime(2024, 7, 22, 11, 51, 39, 392000),
                updated_at=datetime(2024, 7, 22, 11, 57, 3, 446000),
            )
        ]
        response = await self.service.stream_complete_async(
            messages=self.test_messages,
            model_name=self.model_name,
            content_chunks=content_chunks,
        )

        assert response is not None
        assert isinstance(response.message.text, str)

    @pytest.mark.asyncio
    async def test_complete_with_tool_async(self):
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.USER,
                    content="What's the weather in New York?",
                )
            ]
        )

        response = await self.service.complete_async(
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_4_0613,
            tools=[weather_tool],
        )

        assert response.choices[0].message.tool_calls is not None
        assert response.choices[0].message.tool_calls[0].function.name == "get_weather"

    @pytest.mark.asyncio
    async def test_stream_complete_with_tool_async(self):
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.USER,
                    content="What's the weather in New York?",
                )
            ]
        )

        response = await self.service.stream_complete_async(
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_4_0613,
            tools=[weather_tool],
        )

        assert response.tool_calls is not None
        assert response.tool_calls[0].name == "get_weather"

