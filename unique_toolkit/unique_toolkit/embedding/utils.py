import numpy as np
import tiktoken


def count_tokens(text: str, encoding_model="cl100k_base") -> int:
    """
    Counts the number of tokens in the provided text.

    This function encodes the input text using a predefined encoding scheme
    and returns the number of tokens in the encoded text.

    Parameters:
    - text (str): The text to count tokens for.

    Returns:
    - int: The number of tokens in the text.
    """
    encoding = tiktoken.get_encoding(encoding_model)
    return len(encoding.encode(text))


def calculate_cosine_similarity(
    embedding_1: list[float],
    embedding_2: list[float],
) -> float:
    """Get cosine similarity."""
    return np.dot(embedding_1, embedding_2) / (
        np.linalg.norm(embedding_1) * np.linalg.norm(embedding_2)
    )
