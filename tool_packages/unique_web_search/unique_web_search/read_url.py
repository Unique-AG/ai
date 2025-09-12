from enum import Enum
from time import time
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field
from tiktoken import get_encoding
from typing_extensions import override
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.language_model import (
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelToolMessage,
)
from unique_toolkit.tools.factory import ToolFactory
from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.tools.tool import AgentChunksHandler, Tool
from unique_toolkit.tools.tool_progress_reporter import ProgressState

from unique_web_search.config import WebSearchConfig
from unique_web_search.services.content_adapter import ContentAdapter
from unique_web_search.services.crawlers import get_crawler_service


class Step(BaseModel):
    message: str
    error_message: str


class ExecutionSteps(Enum):
    SELECT_URL = Step(
        message="Selecting the URL", error_message="Failed to select the url"
    )
    CRAWL_URL = Step(
        message="Reading content from URL", error_message="Failed to crawl the url"
    )
    ANALYZE_CONTENT = Step(
        message="Analyzing the content", error_message="Failed to analyze the content"
    )


class WebReadUrlToolParameters(BaseModel):
    """Parameters for the WebReadUrl tool."""

    model_config = ConfigDict(extra="forbid")
    url: str = Field(description="")


class WebReadUrlTool(Tool[WebSearchConfig]):
    name = "WebReadUrl"

    def __init__(self, configuration: WebSearchConfig, *args, **kwargs):
        super().__init__(configuration, *args, **kwargs)

        self.index = 1000
        self.crawler = get_crawler_service(self.config.crawler_config)
        self.content_adapter = ContentAdapter(
            event=self.event,
            config=self.config.content_adapter_config,
            llm_service=self._language_model_service,
            language_model=self.config.language_model,
        )

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description="Read the content of a given URL",
            parameters=WebReadUrlToolParameters,
        )

    def tool_description_for_system_prompt(self) -> str:
        return "Read the content of a given URL"

    def tool_format_information_for_system_prompt(self) -> str:
        return ""

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return self.config.evaluation_check_list

    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        evaluation_check_list = self.evaluation_check_list()

        # Check if the tool response is empty
        if not tool_response.content_chunks:
            return []
        return evaluation_check_list

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        """Run search and generate answer to the user query"""
        self.logger.info("Running the WebSearch tool")
        name = "**Web Read Url**"
        step = ExecutionSteps.SELECT_URL

        debug_info = {
            "crawler": self.crawler.__class__.__name__,
        }

        try:
            await self.report_progress(
                name=name,
                message=step.value.message,
                tool_call=tool_call,
                state=ProgressState.RUNNING,
            )
            # Step 1: Parse and validate tool parameters, extract the URL to read
            url, url_domain = await self._validate_tool_parameters(
                tool_call=tool_call,
                name=name,
                message=step.value.message,
            )
            debug_info["url"] = url

            name = f"**Web Read Url**: {url_domain}"
            # Step 2: Crawl the URL
            step = ExecutionSteps.CRAWL_URL

            crawl_start_time = time()
            markdown_content = await self._crawl_url(
                tool_call=tool_call,
                name=name,
                message=step.value.message,
                url=url,
            )
            debug_info = debug_info | {
                "crawl_time": time() - crawl_start_time,
                "markdown_content": markdown_content,
            }

            # step 3: Analyze the content
            step = ExecutionSteps.ANALYZE_CONTENT
            markdown_content = await self._limit_to_token_limit(
                tool_call=tool_call,
                name=name,
                message=step.value.message,
                markdown_content=markdown_content,
            )

            # Step 4: Return Results
            await self.report_progress(
                name=name,
                message=step.value.message,
                tool_call=tool_call,
                state=ProgressState.FINISHED,
            )
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                content=markdown_content,
                debug_info=debug_info,
            )

        except Exception as e:
            await self.report_progress(
                name=name,
                message=step.value.message,
                tool_call=tool_call,
                state=ProgressState.FAILED,
            )
            debug_info = debug_info | {
                "error_message": step.value.error_message,
            }
            self.logger.exception(f"An error occurred while reading the URL: {e}")
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                error_message=step.value.error_message,
                debug_info=debug_info,
            )

    async def _validate_tool_parameters(
        self, tool_call: LanguageModelFunction, name: str, message: str
    ) -> tuple[str, str]:
        await self.report_progress(
            name=name,
            message=message,
            tool_call=tool_call,
            state=ProgressState.RUNNING,
        )
        # Step 1: Parse and validate tool parameters, extract the URL to read
        parameters = WebReadUrlToolParameters.model_validate(
            tool_call.arguments,
        )
        url = parameters.url
        url_domain = urlparse(url).netloc
        return url, url_domain

    async def _crawl_url(
        self, tool_call: LanguageModelFunction, name: str, message: str, url: str
    ) -> str:
        # Step 2: Crawl the URL
        await self.report_progress(
            name=name,
            message=message,
            tool_call=tool_call,
            state=ProgressState.RUNNING,
        )
        content = await self.crawler.crawl([url])

        if not content:
            raise ValueError("No Markdown has been retrieved from the URL")

        markdown_content = content[0]

        return markdown_content

    async def _limit_to_token_limit(
        self,
        tool_call: LanguageModelFunction,
        name: str,
        message: str,
        markdown_content: str,
    ) -> str:
        await self.report_progress(
            name=name,
            message=message,
            tool_call=tool_call,
            state=ProgressState.RUNNING,
        )
        encoder = get_encoding(self.config.language_model.encoder_name)
        token_limit = (
            self.config.percentage_of_input_tokens_for_sources
            * self.config.language_model.token_limits.token_limit_input
        )
        tokens = encoder.encode(markdown_content)
        if len(tokens) > token_limit:
            markdown_content = encoder.decode(tokens[:token_limit])

        return markdown_content

    async def report_progress(
        self,
        name: str,
        message: str,
        tool_call: LanguageModelFunction,
        state: ProgressState,
    ):
        if self.tool_progress_reporter:
            await self.tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name=name,
                message=message,
                state=state,
            )

    def get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
        agent_chunks_handler: AgentChunksHandler,
    ) -> LanguageModelMessage:
        """Process the results of the tool.

        Args:
        ----
            tool_response: The tool response.
            loop_history: The loop history.

        Returns:
        -------
            The tool result to append to the loop history.

        """
        # Append the result to the history
        return LanguageModelToolMessage(
            content=tool_response.content,
            tool_call_id=tool_response.id,  # type: ignore
            name=tool_response.name,
        )


ToolFactory.register_tool(WebReadUrlTool, WebSearchConfig)
