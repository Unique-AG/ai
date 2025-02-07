import logging

import unique_sdk

from unique_toolkit.embedding.constants import DEFAULT_TIMEOUT, DOMAIN_NAME
from unique_toolkit.embedding.schemas import Embeddings

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


def embed_texts(
    user_id: str,
    company_id: str,
    texts: list[str],
    timeout: int = DEFAULT_TIMEOUT,
) -> Embeddings:
    """
    Embed text.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        texts (list[str]): The texts to embed.
        timeout (int): The timeout in milliseconds. Defaults to 600000.

    Returns:
        Embeddings: The Embedding object.

    Raises:
        Exception: If an error occurs.
    """

    try:
        data = {
            "user_id": user_id,
            "company_id": company_id,
            "texts": texts,
            "timeout": timeout,
        }
        response = unique_sdk.Embeddings.create(**data)
        return Embeddings(**response)
    except Exception as e:
        logger.error(f"Error embedding texts: {e}")
        raise e


async def embed_texts_async(
    user_id: str,
    company_id: str,
    texts: list[str],
    timeout: int = DEFAULT_TIMEOUT,
) -> Embeddings:
    """
    Embed text asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        texts (list[str]): The texts to embed.
        timeout (int): The timeout in milliseconds. Defaults to 600000.

    Returns:
        Embeddings: The Embedding object.

    Raises:
        Exception: If an error occurs.
    """
    try:
        data = {
            "user_id": user_id,
            "company_id": company_id,
            "texts": texts,
            "timeout": timeout,
        }
        response = await unique_sdk.Embeddings.create_async(**data)
        return Embeddings(**response)
    except Exception as e:
        logger.error(f"Error embedding texts: {e}")
        raise e
