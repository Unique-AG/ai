from pathlib import Path

from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
)

from _common.agents.loop_agent.config import LoopAgentTokenLimitsConfig
from _common.agents.loop_agent.services.evaluation.config import (
    EvaluationConfig,
)
from _common.chunk_relevancy_sorter.config import ChunkRelevancySortConfig
from _common.evaluators.hallucination.constants import HallucinationConfig
from _common.follow_up_question_v2.config import FollowUpQuestionsConfig
from _common.stock_ticker import (
    StockTickerConfig,
    StockTickerDetectionConfig,
)
from _common.tools.config import ToolBuildConfig, ToolIcon
from _common.tools.internal_search.service import (
    InternalSearchConfig,
    InternalSearchTool,
)
from _common.tools.read_content.config import ReadContentToolConfig
from _common.tools.read_content.service import ReadContentTool
from _common.tools.web_search.service import WebSearchConfig, WebSearchTool
from _common.tools.web_search.services.search_engine.bing import BingConfig
from _common.utils.write_configuration import write_service_configuration
from unique_ai.config import (
    SearchAgentConfig,
    UploadedContentConfig,
)

if __name__ == "__main__":
    big_llm = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_2024_1120,
    )
    small_llm = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
    )

    chunk_relevancy_sort_config = ChunkRelevancySortConfig(
        language_model=small_llm,
        relevancy_levels_to_consider=["high", "medium"],
        enabled=False,
    )

    internal_search_tool = ToolBuildConfig(
        name=InternalSearchTool.name,
        display_name="Document Search",
        is_exclusive=False,
        icon=ToolIcon.BOOK,
        configuration=InternalSearchConfig(
            max_tokens_for_sources=30_000,
            chunk_relevancy_sort_config=chunk_relevancy_sort_config,
            scope_to_chat_on_upload=False,
        ),
    )

    websearch_tool = ToolBuildConfig(
        name=WebSearchTool.name,
        display_name="Web Search",
        is_exclusive=False,
        icon=ToolIcon.BOOK,
        configuration=WebSearchConfig(
            limit_token_sources=30_000,
            language_model=big_llm,
            chunk_relevancy_sort_config=chunk_relevancy_sort_config,
            search_engine_config=BingConfig(
                fetch_size=15,
            ),
        ),
    )

    chat_with_uploaded_content_tool = ToolBuildConfig(
        name=ReadContentTool.name,
        display_name="",
        configuration=ReadContentToolConfig(
            full_sources_serialize_dump=False,
        ),
    )

    follow_up_question_config = FollowUpQuestionsConfig(
        language_model=big_llm,
        number_of_questions=2,
        adapt_to_language=True,
    )

    stock_ticker_config = StockTickerConfig(
        detection_config=StockTickerDetectionConfig(
            language_model=small_llm,
        ),
        enabled=False,
    )

    config = SearchAgentConfig(
        language_model=big_llm,
        tools=[
            internal_search_tool,
            websearch_tool,
            chat_with_uploaded_content_tool,
        ],
        follow_up_questions_config=follow_up_question_config,
        evaluation_config=EvaluationConfig(
            max_review_steps=0,
            hallucination_config=HallucinationConfig(language_model=big_llm),
        ),
        max_loop_iterations=8,
        stock_ticker_config=stock_ticker_config,
        token_limits=LoopAgentTokenLimitsConfig(
            language_model=big_llm,
            percent_of_max_tokens_for_history=0.2,
        ),
        uploaded_content_config=UploadedContentConfig(
            approximate_max_tokens_for_uploaded_content_stuff_context_window=80_000,
        ),
    )

    write_service_configuration(
        service_folderpath=Path(__file__).parent.parent,
        write_folderpath=Path(__file__).parent,
        config=config,
    )
