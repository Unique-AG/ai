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
    ElicitationCancelledException,
    ElicitationDeclinedException,
    ElicitationExpiredException,
    ElicitationFailedException,
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

    async def __call__(self, queries: list[str]) -> list[str]:
        try:
            _LOGGER.info("Creating elicitation...")

            model = QueryElicitationModel.create_model_with_default_queries(queries)
            elicitation = await self._chat_service.elicitation.create_async(
                mode=ElicitationMode.FORM,
                tool_name=self._display_name,
                message="Approve Web Search?",
                json_schema=model.model_json_schema(),
                expires_in_seconds=self._timeout_seconds,
            )
            _LOGGER.info(
                f"Elicitation created: {elicitation.id}. Waiting for user response for {self._timeout_seconds} seconds..."
            )

            for _ in range(self._timeout_seconds):
                await asyncio.sleep(1)
                elicitation = await self._chat_service.elicitation.get_async(
                    elicitation_id=elicitation.id,
                )
                if elicitation.status == ElicitationStatus.ACCEPTED:
                    _LOGGER.info(f"Query elicitation {elicitation.id} accepted")
                    return QueryElicitationModel.model_validate(
                        elicitation.response_content
                    ).queries

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
        except (
            ElicitationDeclinedException,
            ElicitationCancelledException,
            ElicitationExpiredException,
        ):
            # Re-raise these specific elicitation exceptions to preserve their messages
            raise
        except Exception as e:
            _LOGGER.exception(f"Error eliciting queries: {e}")
            raise ElicitationFailedException(
                "Unexpected error occurred while eliciting queries"
            )
