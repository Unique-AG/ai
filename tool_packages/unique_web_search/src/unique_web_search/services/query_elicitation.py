"""Query elicitation service for web search.

This module provides functionality for creating and evaluating query elicitations,
allowing users to review and modify proposed search queries before execution.
"""

import asyncio
import logging
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, create_model
from unique_toolkit.chat.service import ChatService
from unique_toolkit.elicitation import (
    Elicitation,
    ElicitationMode,
    ElicitationStatus,
)

_LOGGER = logging.getLogger(__name__)


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
                    description="The queries to search the web for",
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
        timeout_seconds: int = 60,
    ):
        """Initialize the query elicitation service.

        Args:
            chat_service: Service for interacting with chat/elicitation APIs
            display_name: Display name for the tool in elicitation UI
            timeout_seconds: Timeout in seconds for waiting for user approval
        """
        self._chat_service = chat_service
        self._display_name = display_name
        self._timeout_seconds = timeout_seconds

    def get_callbacks(self):
        """Get creator and evaluator callbacks for query elicitation.

        Returns a tuple of two async functions that can be used by executors:
        - creator: Creates an elicitation with pre-populated queries
        - evaluator: Waits for and evaluates the elicitation response

        The callbacks close over this service instance, maintaining Protocol
        compatibility with ElicitationCreator and ElicitationEvaluator.

        Returns:
            Tuple of (creator, evaluator) async callables
        """

        async def creator(queries: list[str]) -> Elicitation:
            """Create an elicitation with the provided queries.

            Args:
                queries: List of query strings to present to the user

            Returns:
                Created elicitation object
            """
            model = QueryElicitationModel.create_model_with_default_queries(queries)
            return await self._chat_service.elicitation.create_async(
                mode=ElicitationMode.FORM,
                tool_name=self._display_name,
                message="Approve Web Search?",
                json_schema=model.model_json_schema(),
                expires_in_seconds=self._timeout_seconds,
            )

        async def evaluator(elicitation_id: str) -> list[str]:
            """Evaluate an elicitation by waiting for user response.

            Polls the elicitation status until it's accepted or times out.

            Args:
                elicitation_id: ID of the elicitation to evaluate

            Returns:
                List of approved/modified queries from the user

            Raises:
                ValueError: If elicitation is not accepted within timeout
            """
            for _ in range(self._timeout_seconds):
                await asyncio.sleep(1)
                elicitation = await self._chat_service.elicitation.get_async(
                    elicitation_id=elicitation_id,
                )
                if elicitation.status == ElicitationStatus.ACCEPTED:
                    _LOGGER.info(f"Query elicitation {elicitation.id} accepted")
                    return QueryElicitationModel.model_validate(
                        elicitation.response_content
                    ).queries

            raise ValueError(f"Query elicitation {elicitation_id} not accepted")

        return creator, evaluator
