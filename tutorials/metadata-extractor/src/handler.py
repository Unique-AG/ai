from quart import current_app as app

import src.prompts as PROMPT
from src.clients.content import ContentClient
from src.constants import DEFAULT_SCHEMA
from src.utilities import find_date, find_topic
from unique_toolkit.chat.service import LanguageModelName
from unique_toolkit.content.utils import count_tokens
from unique_toolkit.language_model import LanguageModelMessages, Prompt
from unique_toolkit.language_model.functions import complete_async
from unique_toolkit.language_model.infos import LanguageModelInfo


class MetadataExtractorHandler:
    def __init__(self, company_id: str, content_client: ContentClient):
        app.logger.info(f"Initializing MetadataHandler for company: {company_id}")
        self.company_id = company_id
        self.content_client = content_client
        self.language_model = self._get_language_model()

    DEFAULT_LANGUAGE_MODEL = LanguageModelName.AZURE_GPT_4o_2024_0806
    DEFAULT_MAX_INPUT_TOKENS = 10_000
    DEFAULT_ENCODER_NAME = "o200k_base"

    async def run(self, content_id):
        app.logger.info(f"Starting metadata extraction for content ID: {content_id}")
        try:
            ###
            # 1. Get chunks and metadata by content id
            ###
            filename, chunks, metadata = await self._get_chunks_and_metadata(content_id)

            ###
            # 2. Extract content metadata
            ###
            content_metadata = await self._extract_content_metadata(chunks)

            ###
            # 3. Extract filename metadata
            ###
            filename_metadata = self._extract_filename_metadata(filename)
            await self._update_metadata(
                content_id,
                metadata,
                {**content_metadata, **filename_metadata},
            )
            await self._rebuild_metadata(content_id)
            app.logger.info(
                f"Metadata extraction completed for content ID: {content_id}"
            )
        except Exception as e:
            app.logger.error(f"Error in run method: {str(e)}", exc_info=True)

    async def _get_chunks_and_metadata(self, content_id):
        app.logger.info(f"Getting chunks and metadata for content ID: {content_id}")
        content = await self.content_client.get_by_id(content_id)
        key = content.get("key", "")
        chunks = [chunk.get("text", "") for chunk in content.get("chunks", [])]
        metadata = content.get("metadata", {})
        return key, chunks, metadata

    async def _update_metadata(
        self, content_id: str, old_metadata: dict, extracted_metadata: dict
    ):
        combined_metadata = {**old_metadata, **extracted_metadata}
        app.logger.info(f"Updating metadata for content ID: {content_id}")

        try:
            await self.content_client.update_metadata(content_id, combined_metadata)
        except Exception as e:
            app.logger.error(
                f"Error in update_metadata method: {str(e)}", exc_info=True
            )

    async def _rebuild_metadata(self, content_id: str):
        try:
            await self.content_client.mark_rebuild_metadata(content_id)
        except Exception as e:
            app.logger.error(
                f"Error in mark_rebuild_metadata method: {str(e)}", exc_info=True
            )

        try:
            await self.content_client.rebuild_metadata()
        except Exception as e:
            app.logger.error(
                f"Error in rebuild_metadata method: {str(e)}", exc_info=True
            )

    def _extract_filename_metadata(self, filename: str):
        return {"date": find_date(filename), "topic": find_topic(filename)}

    async def _extract_content_metadata(self, chunks):
        if chunks:
            batches = self._merge_chunks(chunks)
            metadata = await self._extract_content_metadata_per_batch(
                ###
                # At the moment we only use the first batch, additional logic is needed to handle multiple batches and
                # merge the results after extractiom. This could be done using Structured Output and a LLM call.
                ###
                DEFAULT_SCHEMA,
                batches[0],
            )
            return metadata or {}
        return {}

    async def _extract_content_metadata_per_batch(self, json_schema, text):
        system_prompt = Prompt(PROMPT.SYSTEM)
        user_prompt = Prompt(PROMPT.USER, text=text)
        messages = LanguageModelMessages(
            [
                system_prompt.to_system_msg(),
                user_prompt.to_user_msg(),
            ]
        )

        response = await complete_async(
            model_name=self.language_model.name,
            company_id=self.company_id,
            messages=messages,
            other_options=self._init_other_options_with_response_format(json_schema),
        )
        return response.choices[0].message.parsed

    def _merge_chunks(self, chunks):
        max_input_tokens = self._get_max_input_tokens()
        encoder_name = self._get_encoder_name()

        batches = []
        current_batch = []
        current_batch_tokens = 0

        for chunk in chunks:
            # Count tokens in this chunk
            chunk_tokens = count_tokens(chunk, encoder_name)

            # If adding this chunk would exceed the limit and we already have chunks in the batch
            if current_batch_tokens + chunk_tokens > max_input_tokens and current_batch:
                # Add the current batch to our list of batches
                batches.append("\n".join(current_batch))
                # Start a new batch with this chunk
                current_batch = [chunk]
                current_batch_tokens = chunk_tokens
            else:
                # Add this chunk to the current batch
                current_batch.append(chunk)
                current_batch_tokens += chunk_tokens

        # Don't forget to add the last batch if it's not empty
        if current_batch:
            batches.append("\n".join(current_batch))

        return batches

    def _init_other_options_with_response_format(self, json_schema):
        other_options = {}
        other_options["responseFormat"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "Metadata",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": json_schema,
                    "required": list(json_schema.keys()),
                    "additionalProperties": False,
                },
            },
        }
        return other_options

    def _get_max_input_tokens(self):
        token_limits = self.language_model.token_limits
        max_input_tokens = self.DEFAULT_MAX_INPUT_TOKENS
        if token_limits:
            max_input_tokens = token_limits.token_limit_input
        return max_input_tokens

    def _get_encoder_name(self):
        return (
            self.language_model.encoder_name.value
            if self.language_model.encoder_name
            else self.DEFAULT_ENCODER_NAME
        )

    def _get_language_model(self):
        return LanguageModelInfo.from_name(self.DEFAULT_LANGUAGE_MODEL)
