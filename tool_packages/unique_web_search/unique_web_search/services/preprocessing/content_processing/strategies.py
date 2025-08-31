from logging import getLogger
from typing import Literal

import tiktoken
from pydantic import Field
from unique_toolkit import LanguageModelService
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
)

from unique_web_search.services.preprocessing.content_processing.base import (
    ContentProcessingStartegy,
    ContentProcessingStrategyConfig,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

logger = getLogger(__name__)


class SummarizeWebpageConfig(ContentProcessingStrategyConfig):
    strategy: Literal[ContentProcessingStartegy.SUMMARIZE] = (
        ContentProcessingStartegy.SUMMARIZE
    )

    pre_truncate_to_max_tokens: int = Field(
        default=30000,
        description="Max number of tokens to truncate the page to keep before summarization",
    )

    min_tokens_trigger_summarization: int = Field(
        default=5000,
        description="Min number of tokens to trigger summarization",
    )
    summarization_system_prompt: str = Field(
        default="""You are a helping assistant that generates query focused summarization of a webpage content. The summary should convey any information that is relevant to the query.""",
        description="The system prompt to use for summarization",
    )


async def summarize_webpage(
    llm_service: LanguageModelService,
    query: str,
    page: WebSearchResult,
    model_info: LanguageModelInfo,
    pre_truncate_to_max_tokens: int,
    min_tokens_trigger_summarization: int,
    summarization_system_prompt: str,
) -> WebSearchResult:
    page_content, token_count = await truncate_page_to_max_tokens(
        page,
        model_info.encoder_name,
        pre_truncate_to_max_tokens,
    )

    if token_count < min_tokens_trigger_summarization:
        return page

    logger.info(f"Summarizing webpage ({page.url}) with {token_count} tokens")

    messages = (
        MessagesBuilder()
        .system_message_append(summarization_system_prompt)
        .user_message_append(f"Query: {query}\nWebpage: {page_content}".strip())
        .build()
    )

    response = await llm_service.complete_async(
        messages=messages,
        model_name=model_info.name,
    )

    page.content = response.choices[0].message.content  # type: ignore

    return page


class TruncatePageToMaxTokensConfig(ContentProcessingStrategyConfig):
    strategy: Literal[ContentProcessingStartegy.TRUNCATE] = (
        ContentProcessingStartegy.TRUNCATE
    )

    truncate_to_max_tokens: int = Field(
        default=5000,
        description="Max number of tokens to truncate the page to",
    )


async def truncate_page_to_max_tokens(
    page: WebSearchResult,
    encoder_name: str,
    max_tokens: int,
) -> tuple[WebSearchResult, int]:
    encoder = tiktoken.get_encoding(encoder_name)

    tokens = encoder.encode(page.content)

    token_count = len(tokens)

    if token_count > max_tokens:
        page.content = encoder.decode(tokens[:max_tokens])

    return page, token_count


def get_strategy(
    strategy: ContentProcessingStrategyConfig,
    query: str,
    language_model: LanguageModelInfo,
    llm_service: LanguageModelService,
):
    if isinstance(strategy, SummarizeWebpageConfig):

        async def summarize_webpage_wrapper(
            page: WebSearchResult,
        ) -> WebSearchResult:
            return await summarize_webpage(
                page=page,
                model_info=language_model,
                llm_service=llm_service,
                query=query,
                pre_truncate_to_max_tokens=strategy.pre_truncate_to_max_tokens,
                min_tokens_trigger_summarization=strategy.min_tokens_trigger_summarization,
                summarization_system_prompt=strategy.summarization_system_prompt,
            )

        return summarize_webpage_wrapper

    elif isinstance(strategy, TruncatePageToMaxTokensConfig):

        async def truncate_page_to_max_tokens_wrapper(
            page: WebSearchResult,
        ) -> WebSearchResult:
            page, _ = await truncate_page_to_max_tokens(
                page=page,
                encoder_name=language_model.encoder_name,
                max_tokens=strategy.truncate_to_max_tokens,
            )
            return page

        return truncate_page_to_max_tokens_wrapper
    else:
        raise ValueError(f"Invalid strategy: {strategy}")
