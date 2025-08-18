import hashlib
import re


import tiktoken
from unique_toolkit.content.schemas import Content, ContentReference
from unique_toolkit.unique_toolkit.base_agents.loop_agent.history_manager.utils import transform_chunks_to_string


def remove_source_tags(input_string: str) -> str:
    """
    Remove all source tags (e.g. [source1]) from the input string.

    Args:
        input_string: The input string to remove the source tags from.

    Returns:
        result: The input string with the source tags removed.
    """

    # Define the regular expression pattern to match [sourceX] where X is any number
    pattern = r"\[source\d+\]"

    # Use re.sub to replace all occurrences of the pattern with an empty string
    result = re.sub(pattern, "", input_string)
    return result



def create_content_reference(
    content: Content, message_id: str, sequence_number: int
) -> ContentReference:
    """Create a ContentReference object from the given content and chat message details."""
    return ContentReference(
        id=content.id,
        message_id=message_id,
        name=content.key,
        sequence_number=sequence_number,
        source="",
        source_id=content.id,
        url=content.url or f"unique://content/{content.id}",
    )


def get_approximate_token_count_sources(
    chat_uploaded_files: list[Content], encoder_name: str
) -> int:
    if len(chat_uploaded_files) == 0:
        return 0
    encoder = tiktoken.get_encoding(encoder_name)
    chunks = [
        chunk for content in chat_uploaded_files for chunk in content.chunks
    ]
    approximate_token_count_sources = len(
        encoder.encode(transform_chunks_to_string(chunks, 0, None, True))
    )
    return approximate_token_count_sources


 # TODO: Make this better
def filter_duplicates_from_list_on_string_representation(
    obs: list,
) -> list:
    dedup_list = []
    seen = set()

    for ob in obs:
        h = hashlib.sha256(ob.__str__().encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            dedup_list.append(ob)
    return dedup_list