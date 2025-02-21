import re

import tiktoken
import unique_sdk

from unique_toolkit.content.schemas import (
    Content,
    ContentChunk,
)


def _map_content_id_to_chunks(content_chunks: list[ContentChunk]):
    doc_id_to_chunks: dict[str, list[ContentChunk]] = {}
    for chunk in content_chunks:
        source_chunks = doc_id_to_chunks.get(chunk.id)
        if not source_chunks:
            doc_id_to_chunks[chunk.id] = [chunk]
        else:
            source_chunks.append(chunk)
    return doc_id_to_chunks


def sort_content_chunks(content_chunks: list[ContentChunk]):
    """
    Sorts the content chunks based on their 'order' in the original content.
    This function sorts the search results based on their 'order' in ascending order.
    It also performs text modifications by replacing the string within the tags <|/content|>
    with 'text part {order}' and removing any <|info|> tags (Which is useful in referencing the chunk).
    Parameters:
    - content_chunks (list): A list of ContentChunkt objects.
    Returns:
    - list: A list of ContentChunk objects sorted according to their order.
    """
    doc_id_to_chunks = _map_content_id_to_chunks(content_chunks)
    sorted_chunks: list[ContentChunk] = []
    for chunks in doc_id_to_chunks.values():
        chunks.sort(key=lambda x: x.order)
        for i, s in enumerate(chunks):
            s.text = re.sub(
                r"<\|/content\|>", f" text part {s.order}<|/content|>", s.text
            )
            s.text = re.sub(r"<\|info\|>(.*?)<\|\/info\|>", "", s.text)
            pages_postfix = _generate_pages_postfix([s])
            s.key = s.key + pages_postfix if s.key else s.key
            s.title = s.title + pages_postfix if s.title else s.title
        sorted_chunks.extend(chunks)
    return sorted_chunks


def merge_content_chunks(content_chunks: list[ContentChunk]):
    """
    Merges multiple search results based on their 'id', removing redundant content and info markers.

    This function groups search results by their 'id' and then concatenates their texts,
    cleaning up any content or info markers in subsequent chunks beyond the first one.

    Parameters:
    - content_chunks (list): A list of objects, each representing a search result with 'id' and 'text' keys.

    Returns:
    - list: A list of objects with merged texts for each unique 'id'.
    """

    doc_id_to_chunks = _map_content_id_to_chunks(content_chunks)
    merged_chunks: list[ContentChunk] = []
    for chunks in doc_id_to_chunks.values():
        chunks.sort(key=lambda x: x.order)
        for i, s in enumerate(chunks):
            ## skip first element
            if i > 0:
                ## replace the string within the tags <|content|>...<|/content|> and <|info|> and <|/info|>
                s.text = re.sub(r"<\|content\|>(.*?)<\|\/content\|>", "", s.text)
                s.text = re.sub(r"<\|info\|>(.*?)<\|\/info\|>", "", s.text)

        pages_postfix = _generate_pages_postfix(chunks)
        chunks[0].text = "\n".join(str(s.text) for s in chunks)
        chunks[0].key = (
            chunks[0].key + pages_postfix if chunks[0].key else chunks[0].key
        )
        chunks[0].title = (
            chunks[0].title + pages_postfix if chunks[0].title else chunks[0].title
        )
        chunks[0].end_page = chunks[-1].end_page
        merged_chunks.append(chunks[0])

    return merged_chunks


def _generate_pages_postfix(chunks: list[ContentChunk]) -> str:
    """
    Generates a postfix string of page numbers from a list of source objects.
    Each source object contains startPage and endPage numbers. The function
    compiles a list of all unique page numbers greater than 0 from all chunks,
    and then returns them as a string prefixed with " : " if there are any.

    Parameters:
    - chunks (list): A list of objects with 'startPage' and 'endPage' keys.

    Returns:
    - string: A string of page numbers separated by commas, prefixed with " : ".
    """

    def gen_all_numbers_in_between(start, end) -> list[int]:
        """
        Generates a list of all numbers between start and end, inclusive.
        If start or end is -1, it behaves as follows:
        - If both start and end are -1, it returns an empty list.
        - If only end is -1, it returns a list containing only the start.
        - If start is -1, it returns an empty list.

        Parameters:
        - start (int): The starting page number.
        - end (int): The ending page number.

        Returns:
        - list: A list of numbers from start to end, inclusive.
        """
        if start == -1 and end == -1:
            return []
        if end == -1:
            return [start]
        if start == -1:
            return []
        return list(range(start, end + 1))

    page_numbers_array = [
        gen_all_numbers_in_between(c.start_page, c.end_page) for c in chunks
    ]
    page_numbers = [number for sublist in page_numbers_array for number in sublist]
    page_numbers = [p for p in page_numbers if p > 0]
    page_numbers = sorted(set(page_numbers))
    pages_postfix = (
        " : " + ",".join(str(p) for p in page_numbers) if page_numbers else ""
    )
    return pages_postfix


def pick_content_chunks_for_token_window(
    content_chunks: list[ContentChunk],
    token_limit: int,
    encoding_model="cl100k_base",
):
    """
    Selects and returns a list of search results that fit within a specified token limit.

    This function iterates over a list of search results, each with a 'text' field, and
    encodes the text using a predefined encoding scheme. It accumulates search results
    until the token limit is reached or exceeded.

    Parameters:
    - content_chunks (list): A list of dictionaries, each containing a 'text' key with string value.
    - token_limit (int): The maximum number of tokens to include in the output.

    Returns:
    - list: A list of dictionaries representing the search results that fit within the token limit.
    """
    picked_chunks: list[ContentChunk] = []
    token_count = 0

    encoding = tiktoken.get_encoding(encoding_model)

    for chunk in content_chunks:
        try:
            searchtoken_count = len(encoding.encode(chunk.text))
        except Exception:
            searchtoken_count = 0
        if token_count + searchtoken_count > token_limit:
            break

        picked_chunks.append(chunk)
        token_count += searchtoken_count

    return picked_chunks


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


def map_content_chunk(content_chunk: dict):
    return ContentChunk(
        id=content_chunk["id"],
        text=content_chunk["text"],
        start_page=content_chunk["startPage"],
        end_page=content_chunk["endPage"],
        order=content_chunk["order"],
    )


def map_content(content: dict):
    return Content(
        id=content["id"],
        key=content["key"],
        title=content["title"],
        url=content["url"],
        chunks=[map_content_chunk(chunk) for chunk in content["chunks"]],
        created_at=content["createdAt"],
        updated_at=content["updatedAt"],
    )


def map_contents(contents):
    return [map_content(content) for content in contents]


def map_to_content_chunks(searches: list[unique_sdk.Search]):
    return [ContentChunk(**search) for search in searches]
