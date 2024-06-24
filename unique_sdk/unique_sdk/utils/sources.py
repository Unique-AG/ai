import re


def sort_sources(searchContext) -> list[str]:
    """
    Sorts the search results based on their 'order' in the original document.
    This function sorts the search results based on their 'order' in ascending order.
    It also performs text modifications by replacing the string within the tags <|/document|>
    with 'text part {order}' and removing any <|info|> tags (Which is useful in referencing the chunk).
    Parameters:
    - searchContext (list): A list of SearchResult objects.
    Returns:
    - list: A list of SearchResult objects sorted according to their order.
    """
    sourceMap = {}
    for result in searchContext:
        sourceChunks = sourceMap.get(result.id)
        if not sourceChunks:
            sourceMap[result.id] = [result]
        else:
            sourceChunks.append(result)
    sortedSources = []
    for sources in sourceMap.values():
        sources.sort(key=lambda x: x.order)
        for i, s in enumerate(sources):
            s.text = re.sub(
                r"<\|/document\|>", f' text part {s["order"]}<|/document|>', s["text"]
            )
            s.text = re.sub(r"<\|info\|>(.*?)<\|\/info\|>", "", s.text)
            pages_postfix = generate_pages_postfix([s])
            s.key = s.key + pages_postfix if s.key else s.key
            s.title = s.title + pages_postfix if s.title else s.title
        sortedSources.extend(sources)
    return sortedSources


def merge_sources(searchContext) -> list[str]:
    """
    Merges multiple search results based on their 'id', removing redundant document and info markers.

    This function groups search results by their 'id' and then concatenates their texts,
    cleaning up any document or info markers in subsequent chunks beyond the first one.

    Parameters:
    - searchContext (list): A list of objects, each representing a search result with 'id' and 'text' keys.

    Returns:
    - list: A list of objects with merged texts for each unique 'id'.
    """

    sourceMap = {}
    for result in searchContext:
        sourceChunks = sourceMap.get(result.id)
        if not sourceChunks:
            sourceMap[result.id] = [result]
        else:
            sourceChunks.append(result)

    mergedSources = []
    for sources in sourceMap.values():
        sources.sort(key=lambda x: x.order)
        for i, s in enumerate(sources):
            ## skip first element
            if i > 0:
                ## replace the string within the tags <|document|>...<|/document|> and <|info|> and <|/info|>
                s.text = re.sub(r"<\|document\|>(.*?)<\|\/document\|>", "", s.text)
                s.text = re.sub(r"<\|info\|>(.*?)<\|\/info\|>", "", s.text)

        pages_postfix = generate_pages_postfix(sources)
        sources[0].text = "\n".join(str(s.text) for s in sources)
        sources[0].key = (
            sources[0].key + pages_postfix if sources[0].key else sources[0].key
        )
        sources[0].title = (
            sources[0].title + pages_postfix if sources[0].title else sources[0].title
        )
        sources[0].endPage = sources[-1].endPage
        mergedSources.append(sources[0])

    return mergedSources


def generate_pages_postfix(sources) -> str:
    """
    Generates a postfix string of page numbers from a list of source objects.
    Each source object contains startPage and endPage numbers. The function
    compiles a list of all unique page numbers greater than 0 from all sources,
    and then returns them as a string prefixed with " : " if there are any.

    Parameters:
    - sources (list): A list of objects with 'startPage' and 'endPage' keys.

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
        gen_all_numbers_in_between(s.startPage, s.endPage) for s in sources
    ]
    page_numbers = [number for sublist in page_numbers_array for number in sublist]
    page_numbers = [p for p in page_numbers if p > 0]
    page_numbers = sorted(set(page_numbers))
    pages_postfix = (
        " : " + ",".join(str(p) for p in page_numbers) if page_numbers else ""
    )
    return pages_postfix
