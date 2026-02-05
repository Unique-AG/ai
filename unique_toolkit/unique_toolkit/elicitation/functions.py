import logging
from typing import Any

import unique_sdk
from pydantic import AnyUrl

from unique_toolkit.elicitation.constants import DOMAIN_NAME
from unique_toolkit.elicitation.schemas import (
    CreateElicitationParams,
    Elicitation,
    ElicitationAction,
    ElicitationList,
    ElicitationMode,
    ElicitationResponseResult,
    RespondToElicitationParams,
)

_LOGGER = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


def create_elicitation(
    user_id: str,
    company_id: str,
    *,
    mode: ElicitationMode,
    message: str,
    tool_name: str,
    json_schema: dict[str, Any] | None = None,
    url: str | None = None,
    external_elicitation_id: str | None = None,
    chat_id: str | None = None,
    message_id: str | None = None,
    expires_in_seconds: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> Elicitation:
    """
    Create an elicitation request synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        mode (Literal["FORM", "URL"]): The elicitation mode.
        message (str): The message to display to the user.
        tool_name (str): The name of the tool requesting elicitation.
        json_schema (dict[str, Any], optional): JSON schema for FORM mode.
        url (str, optional): URL for URL mode.
        external_elicitation_id (str, optional): External elicitation ID for tracking.
        chat_id (str, optional): The chat ID if elicitation is associated with a chat.
        message_id (str, optional): The message ID if elicitation is associated with a message.
        expires_in_seconds (int, optional): Expiration time in seconds.
        metadata (dict[str, Any], optional): Additional metadata.

    Returns:
        Elicitation: The created elicitation.

    Raises:
        Exception: If the creation fails.
    """
    _LOGGER.info(f"Creating elicitation in {mode} mode for tool: {tool_name}")
    try:
        url_obj = AnyUrl(url) if url else None

        params_obj = CreateElicitationParams(
            mode=mode,
            message=message,
            tool_name=tool_name,
            json_schema=json_schema,
            url=url_obj,
            external_elicitation_id=external_elicitation_id,
            chat_id=chat_id,
            message_id=message_id,
            expires_in_seconds=expires_in_seconds,
            metadata=metadata,
        )

        params = params_obj.model_dump(by_alias=True, exclude_none=True)

        response = unique_sdk.Elicitation.create_elicitation(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return Elicitation.model_validate(response)
    except Exception as e:
        _LOGGER.exception(f"Error creating elicitation: {e}")
        raise e


async def create_elicitation_async(
    user_id: str,
    company_id: str,
    *,
    mode: ElicitationMode,
    message: str,
    tool_name: str,
    json_schema: dict[str, Any] | None = None,
    url: str | None = None,
    external_elicitation_id: str | None = None,
    chat_id: str | None = None,
    message_id: str | None = None,
    expires_in_seconds: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> Elicitation:
    """
    Create an elicitation request asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        mode (Literal["FORM", "URL"]): The elicitation mode.
        message (str): The message to display to the user.
        tool_name (str): The name of the tool requesting elicitation.
        json_schema (dict[str, Any], optional): JSON schema for FORM mode.
        url (str, optional): URL for URL mode.
        external_elicitation_id (str, optional): External elicitation ID for tracking.
        chat_id (str, optional): The chat ID if elicitation is associated with a chat.
        message_id (str, optional): The message ID if elicitation is associated with a message.
        expires_in_seconds (int, optional): Expiration time in seconds.
        metadata (dict[str, Any], optional): Additional metadata.

    Returns:
        Elicitation: The created elicitation.

    Raises:
        Exception: If the creation fails.
    """
    _LOGGER.info(f"Creating elicitation (async) in {mode} mode for tool: {tool_name}")
    try:
        url_obj = AnyUrl(url) if url else None
        params_obj = CreateElicitationParams(
            mode=mode,
            message=message,
            tool_name=tool_name,
            json_schema=json_schema,
            url=url_obj,
            external_elicitation_id=external_elicitation_id,
            chat_id=chat_id,
            message_id=message_id,
            expires_in_seconds=expires_in_seconds,
            metadata=metadata,
        )

        params = params_obj.model_dump(by_alias=True, exclude_none=True)

        response = await unique_sdk.Elicitation.create_elicitation_async(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return Elicitation.model_validate(response)
    except Exception as e:
        _LOGGER.exception(f"Error creating elicitation: {e}")
        raise e


def get_elicitation(
    user_id: str,
    company_id: str,
    elicitation_id: str,
) -> Elicitation:
    """
    Get an elicitation request by ID synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        elicitation_id (str): The elicitation ID.

    Returns:
        Elicitation: The elicitation.

    Raises:
        Exception: If the request fails.
    """
    _LOGGER.info(f"Getting elicitation: {elicitation_id}")
    try:
        response = unique_sdk.Elicitation.get_elicitation(
            user_id=user_id,
            company_id=company_id,
            elicitation_id=elicitation_id,
        )
        return Elicitation.model_validate(response, by_alias=True)
    except Exception as e:
        _LOGGER.exception(f"Error getting elicitation {elicitation_id}: {e}")
        raise e


async def get_elicitation_async(
    user_id: str,
    company_id: str,
    elicitation_id: str,
) -> Elicitation:
    """
    Get an elicitation request by ID asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        elicitation_id (str): The elicitation ID.

    Returns:
        Elicitation: The elicitation.

    Raises:
        Exception: If the request fails.
    """
    _LOGGER.info(f"Getting elicitation (async): {elicitation_id}")
    try:
        response = await unique_sdk.Elicitation.get_elicitation_async(
            user_id=user_id,
            company_id=company_id,
            elicitation_id=elicitation_id,
        )
        return Elicitation.model_validate(response, by_alias=True)
    except Exception as e:
        _LOGGER.exception(f"Error getting elicitation {elicitation_id}: {e}")
        raise e


def get_pending_elicitations(
    user_id: str,
    company_id: str,
) -> ElicitationList:
    """
    Get all pending elicitation requests synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.

    Returns:
        ElicitationList: The list of pending elicitations.

    Raises:
        Exception: If the request fails.
    """
    _LOGGER.info("Getting pending elicitations")
    try:
        response = unique_sdk.Elicitation.get_pending_elicitations(
            user_id=user_id,
            company_id=company_id,
        )
        return ElicitationList.model_validate(response, by_alias=True)
    except Exception as e:
        _LOGGER.exception(f"Error getting pending elicitations: {e}")
        raise e


async def get_pending_elicitations_async(
    user_id: str,
    company_id: str,
) -> ElicitationList:
    """
    Get all pending elicitation requests asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.

    Returns:
        ElicitationList: The list of pending elicitations.

    Raises:
        Exception: If the request fails.
    """
    _LOGGER.info("Getting pending elicitations (async)")
    try:
        response = await unique_sdk.Elicitation.get_pending_elicitations_async(
            user_id=user_id,
            company_id=company_id,
        )
        return ElicitationList.model_validate(response, by_alias=True)
    except Exception as e:
        _LOGGER.exception(f"Error getting pending elicitations: {e}")
        raise e


def respond_to_elicitation(
    user_id: str,
    company_id: str,
    elicitation_id: str,
    *,
    action: ElicitationAction,
    content: dict[str, str | int | bool | list[str]] | None = None,
) -> ElicitationResponseResult:
    """
    Respond to an elicitation request synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        elicitation_id (str): The elicitation ID.
        action (Literal["ACCEPT", "DECLINE", "CANCEL"]): The action to take.
        content (dict[str, str | int | bool | list[str]], optional): Response content for ACCEPT action.

    Returns:
        ElicitationResponseResult: The response result.

    Raises:
        Exception: If the response fails.
    """
    _LOGGER.info(f"Responding to elicitation {elicitation_id} with action: {action}")
    try:
        params_obj = RespondToElicitationParams(
            elicitation_id=elicitation_id,
            action=action,
            content=content,
        )

        params = params_obj.model_dump(by_alias=True, exclude_none=True)

        response = unique_sdk.Elicitation.respond_to_elicitation(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return ElicitationResponseResult.model_validate(response, by_alias=True)
    except Exception as e:
        _LOGGER.exception(f"Error responding to elicitation {elicitation_id}: {e}")
        raise e


async def respond_to_elicitation_async(
    user_id: str,
    company_id: str,
    elicitation_id: str,
    *,
    action: ElicitationAction,
    content: dict[str, str | int | bool | list[str]] | None = None,
) -> ElicitationResponseResult:
    """
    Respond to an elicitation request asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        elicitation_id (str): The elicitation ID.
        action (Literal["ACCEPT", "DECLINE", "CANCEL"]): The action to take.
        content (dict[str, str | int | bool | list[str]], optional): Response content for ACCEPT action.

    Returns:
        ElicitationResponseResult: The response result.

    Raises:
        Exception: If the response fails.
    """
    _LOGGER.info(
        f"Responding to elicitation (async) {elicitation_id} with action: {action}"
    )
    try:
        params_obj = RespondToElicitationParams(
            elicitation_id=elicitation_id,
            action=action,
            content=content,
        )

        params = params_obj.model_dump(by_alias=True, exclude_none=True)

        response = await unique_sdk.Elicitation.respond_to_elicitation_async(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return ElicitationResponseResult.model_validate(response, by_alias=True)
    except Exception as e:
        _LOGGER.exception(f"Error responding to elicitation {elicitation_id}: {e}")
        raise e
