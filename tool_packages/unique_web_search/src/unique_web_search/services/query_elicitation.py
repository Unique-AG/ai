"""Query elicitation service for web search.

This module provides functionality for creating and evaluating query elicitations,
allowing users to review and modify proposed search queries before execution.
"""

import asyncio
import logging
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, create_model
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.chat.service import ChatService
from unique_toolkit.elicitation import (
    ElicitationCancelledException,
    ElicitationDeclinedException,
    ElicitationExpiredException,
    ElicitationFailedException,
    ElicitationMode,
    ElicitationStatus,
)

_LOGGER = logging.getLogger(__name__)


class QueryElicitationConfig(BaseModel):
    model_config = get_configuration_dict()

    enable_elicitation: bool = Field(
        default=False,
        description="Whether to enable elicitation. This flag is relevant only if the associated feature flag is enabled.",
    )
    timeout_seconds: int = Field(
        default=60,
        description="Timeout in seconds for waiting for user approval",
        ge=1,
        le=300,
    )


class QueryElicitationModel(BaseModel):
    """Model for query elicitation with support for default values.

    This model uses Pydantic's RootModel to represent a list of queries.
    The create_model_with_default_queries classmethod enables dynamic model
    creation with default values for form pre-population.
    """

    model_config = ConfigDict(title="Query Elicitation")
    queries: list[str] = Field(description="The queries to search the web for")

    @classmethod
    def create_model_with_default_queries(cls, queries: list[str]) -> type[Self]:
        """Create a model with default query values.

        This method dynamically creates a Pydantic model where the root field
        has default values set to the provided queries. This allows elicitation
        forms to be pre-populated with suggested queries that users can review
        and modify.

        Args:
            queries: List of default query strings to pre-populate

        Returns:
            A new model class with default values set
        """
        model = create_model(
            cls.__name__,
            queries=(
                list[str],
                Field(
                    default=queries,
                ),
            ),
            __base__=cls,
        )
        return model


class QueryElicitationService:
    """Service for managing query elicitation workflow.

    This service encapsulates the logic for creating elicitations and waiting
    for user approval, providing a clean callback-based interface for integration
    with web search executors.
    """

    def __init__(
        self,
        chat_service: ChatService,
        display_name: str,
        config: QueryElicitationConfig,
    ):
        """Initialize the query elicitation service.

        Args:
            chat_service: Service for interacting with chat/elicitation APIs
            display_name: Display name for the tool in elicitation UI
            timeout_seconds: Timeout in seconds for waiting for user approval
        """
        self._chat_service = chat_service
        self._display_name = display_name
        self._config = config

    async def __call__(self, queries: list[str]) -> list[str]:
        if not self._config.enable_elicitation:
            return queries

        _LOGGER.info("Creating elicitation...")

        model = QueryElicitationModel.create_model_with_default_queries(queries)
        elicitation = await self._chat_service.elicitation.create_async(
            mode=ElicitationMode.FORM,
            tool_name=self._display_name,
            message="Web Search Query Approval",
            json_schema=model.model_json_schema(),
            expires_in_seconds=self._config.timeout_seconds,
        )
        _LOGGER.info(
            f"Elicitation created: {elicitation.id}. Waiting for user response for {self._config.timeout_seconds} seconds..."
        )

        for _ in range(self._config.timeout_seconds):
            await asyncio.sleep(1)
            elicitation = await self._chat_service.elicitation.get_async(
                elicitation_id=elicitation.id,
            )
            if elicitation.status == ElicitationStatus.ACCEPTED:
                _LOGGER.info(f"Query elicitation {elicitation.id} accepted")
                queries = QueryElicitationModel.model_validate(
                    elicitation.response_content
                ).queries

                if len(queries) == 0:
                    raise ElicitationFailedException(
                        context="The user approved the web search request but removed all search queries from the form, resulting in zero queries to execute.",
                        instruction="The web search tool did not execute because no search queries were provided. "
                        "**IMPORTANT INFORMATION TO PROPAGATE TO THE USER:** The user was presented with an approval form (elicitation UI) showing the proposed search queries before execution. "
                        "They clicked 'Approve' or submitted the form, but all search query fields were either removed or left empty. "
                        "Because of this, the web search tool cannot perform any searches - it needs at least one search query to execute. "
                        "Explain this situation clearly to the user and inform them that the search was not performed. "
                        "Ask if they would like to retry the search with specific queries, or if they can describe what information they're looking for so you can help formulate appropriate search queries for the next approval.",
                    )

                return queries

            elif elicitation.status == ElicitationStatus.DECLINED:
                _LOGGER.info(f"Query elicitation {elicitation.id} declined")
                raise ElicitationDeclinedException(
                    f"Elicitation triggerd with queries {queries} was declined"
                )

            elif elicitation.status == ElicitationStatus.CANCELLED:
                _LOGGER.info(f"Query elicitation {elicitation.id} cancelled")
                raise ElicitationCancelledException(
                    f"Elicitation triggerd with queries {queries} was cancelled"
                )

        raise ElicitationExpiredException(
            f"Query elicitation {elicitation.id} not accepted"
        )
