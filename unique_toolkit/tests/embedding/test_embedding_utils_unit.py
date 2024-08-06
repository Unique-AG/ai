import pytest

from unique_toolkit.embedding.utils import calculate_cosine_similarity


class TestEmbeddingUtils:
    def test_get_cosine_similarity(self):
        embedding_1 = [1.0, 0.0, 1.0]
        embedding_2 = [0.0, 1.0, 0.0]
        result = calculate_cosine_similarity(embedding_1, embedding_2)
        expected = 0  # Orthogonal vectors have cosine similarity of 0
        assert pytest.approx(result) == expected

        embedding_1 = [1.0, 1.0, 1.0]
        embedding_2 = [1.0, 1.0, 1.0]
        result = calculate_cosine_similarity(embedding_1, embedding_2)
        expected = 1  # Identical vectors have cosine similarity of 1
        assert pytest.approx(result) == expected
