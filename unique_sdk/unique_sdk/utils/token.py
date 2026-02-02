import tiktoken
from typing_extensions import deprecated


def pick_search_results_for_token_window(
    searchResults, tokenLimit, encoding_model="cl100k_base"
) -> list[str]:
    """
    Selects and returns a list of search results that fit within a specified token limit.

    This function iterates over a list of search results, each with a 'text' field, and
    encodes the text using a predefined encoding scheme. It accumulates search results
    until the token limit is reached or exceeded.

    Parameters:
    - searchResults (list): A list of dictionaries, each containing a 'text' key with string value.
    - tokenLimit (int): The maximum number of tokens to include in the output.

    Returns:
    - list: A list of dictionaries representing the search results that fit within the token limit.
    """
    pickedSearchResults = []
    tokenCount = 0

    encoding = tiktoken.get_encoding(encoding_model)

    for searchResult in searchResults:
        try:
            searchTokenCount = len(encoding.encode(searchResult.text))
        except Exception:
            searchTokenCount = 0
        if tokenCount + searchTokenCount > tokenLimit:
            break

        pickedSearchResults.append(searchResult)
        tokenCount += searchTokenCount

    return pickedSearchResults


@deprecated("Use unique_toolkit._common.token.count_tokens_for_model instead")
def count_tokens(
    text: str,
    encoding_model: str = "cl100k_base",
) -> int:
    """Deprecated: Use unique_toolkit._common.token.count_tokens_for_model instead."""
    encoding = tiktoken.get_encoding(encoding_model)
    return len(encoding.encode(text))
