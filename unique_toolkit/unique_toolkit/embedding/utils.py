import numpy as np


def calculate_cosine_similarity(
    embedding_1: list[float],
    embedding_2: list[float],
) -> float:
    """Get cosine similarity."""
    return np.dot(embedding_1, embedding_2) / (
        np.linalg.norm(embedding_1) * np.linalg.norm(embedding_2)
    )
