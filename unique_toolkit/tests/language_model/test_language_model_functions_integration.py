from datetime import datetime

import pytest

from unique_toolkit.content.schemas import ContentChunk, ContentMetadata
from unique_toolkit.language_model.functions import (
    complete,
    complete_async,
    stream_complete,
    stream_complete_async,
)
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


class TestLanguageModelFunctionsIntegration:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.company_id = "test_company"
        self.user_id = "test_user"
        self.assistant_message_id = "test_assistant_msg"
        self.user_message_id = "test_user_msg"
        self.chat_id = "test_chat"
        self.assistant_id = "test_assistant"
        self.test_messages = LanguageModelMessages(
            [
                LanguageModelSystemMessage(content="You are Shakespeare"),
                LanguageModelUserMessage(content="Tell a joke"),
            ]
        )
        self.model_name = LanguageModelName.AZURE_GPT_4_0613

    def test_complete(self):
        """Test basic completion without streaming"""
        response = complete(
            company_id=self.company_id,
            messages=self.test_messages,
            model_name=self.model_name,
        )
        assert len(response.choices) == 1
        assert isinstance(response.choices[0].message.content, str)

    def test_complete_with_tool(self):
        """Test completion with tool calling"""
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.USER,
                    content="What's the weather in New York?",
                )
            ]
        )

        response = complete(
            company_id=self.company_id,
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_4_0613,
            tools=[weather_tool],
        )

        assert response.choices[0].message.tool_calls is not None
        assert response.choices[0].message.tool_calls[0].function.name == "get_weather"

    def test_stream_complete(self):
        """Test streaming completion"""
        response = stream_complete(
            company_id=self.company_id,
            user_id=self.user_id,
            assistant_message_id=self.assistant_message_id,
            user_message_id=self.user_message_id,
            chat_id=self.chat_id,
            assistant_id=self.assistant_id,
            messages=self.test_messages,
            model_name=self.model_name,
        )
        assert response is not None
        assert isinstance(response.message.text, str)

    def test_stream_complete_with_search_context(self):
        """Test streaming completion with content chunks"""
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
        response = stream_complete(
            company_id=self.company_id,
            user_id=self.user_id,
            assistant_message_id=self.assistant_message_id,
            user_message_id=self.user_message_id,
            chat_id=self.chat_id,
            assistant_id=self.assistant_id,
            messages=self.test_messages,
            model_name=self.model_name,
            content_chunks=content_chunks,
        )
        assert response is not None
        assert isinstance(response.message.text, str)

    def test_stream_complete_with_tool(self):
        """Test streaming completion with tool calling"""
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.USER,
                    content="What's the weather in New York?",
                )
            ]
        )

        response = stream_complete(
            company_id=self.company_id,
            user_id=self.user_id,
            assistant_message_id=self.assistant_message_id,
            user_message_id=self.user_message_id,
            chat_id=self.chat_id,
            assistant_id=self.assistant_id,
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_4_0613,
            tools=[weather_tool],
        )

        assert response.tool_calls is not None
        assert response.tool_calls[0].name == "get_weather"

    @pytest.mark.asyncio
    async def test_complete_async(self):
        """Test asynchronous completion"""
        response = await complete_async(
            company_id=self.company_id,
            user_id=self.user_id,
            messages=self.test_messages,
            model_name=self.model_name,
        )
        assert len(response.choices) == 1
        assert isinstance(response.choices[0].message.content, str)

    @pytest.mark.asyncio
    async def test_complete_with_tool_async(self):
        """Test asynchronous completion with tool calling"""
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.USER,
                    content="What's the weather in New York?",
                )
            ]
        )

        response = await complete_async(
            company_id=self.company_id,
            user_id=self.user_id,
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_4_0613,
            tools=[weather_tool],
        )

        assert response.choices[0].message.tool_calls is not None
        assert response.choices[0].message.tool_calls[0].function.name == "get_weather"

    @pytest.mark.asyncio
    async def test_stream_complete_async(self):
        """Test asynchronous streaming completion"""
        response = await stream_complete_async(
            company_id=self.company_id,
            user_id=self.user_id,
            assistant_message_id=self.assistant_message_id,
            user_message_id=self.user_message_id,
            chat_id=self.chat_id,
            assistant_id=self.assistant_id,
            messages=self.test_messages,
            model_name=self.model_name,
        )
        assert response is not None
        assert isinstance(response.message.text, str)
