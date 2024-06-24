import tiktoken


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


def count_tokens(text, encoding_model="cl100k_base") -> int:
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
