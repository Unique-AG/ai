import unittest
from datetime import datetime

import pytest

from unique_toolkit.content.schemas import ContentChunk, ContentMetadata
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)
from unique_toolkit.language_model.service import LanguageModelService


@pytest.mark.usefixtures("chat_state")
class TestLanguageModelService(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def setup(self, chat_state):
        # This method will be called before each test
        self.chat_state = chat_state  # You might need to initialize this properly
        self.service = LanguageModelService(self.chat_state)
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
        self.assertEqual(len(response.choices), 1)

        choice = response.choices[0]
        self.assertIsInstance(choice.message.content, str)

    def test_can_stream_complete(self):
        response = self.service.stream_complete(
            messages=self.test_messages,
            model_name=self.model_name,
        )
        self.assertIsNotNone(response)
        self.assertIsInstance(response.message.text, str)

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
        self.assertIsNotNone(response)
        self.assertIsInstance(response.message.text, str)
