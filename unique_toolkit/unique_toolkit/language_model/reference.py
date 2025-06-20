import re

from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.content.schemas import ContentChunk, ContentReference


def add_references_to_message(
    message: ChatMessage,
    search_context: list[ContentChunk],
    model: str | None = None,
) -> tuple[ChatMessage, bool]:
    """Add references to a message and return the updated message with change status.

    Returns:
        Tuple[ChatMessage, bool]: (updated_message, references_changed)
    """
    if not message.content:
        return message, False

    if message.id is None:
        raise ValueError("Message ID is required")

    message.content = _preprocess_message(message.content)
    text, ref_found = _add_references(
        message.content, search_context, message.id, model
    )
    message.content = _postprocess_message(text)

    message.references = ref_found
    references_changed = len(ref_found) > 0
    return message, references_changed


def _add_references(
    text: str,
    search_context: list[ContentChunk],
    message_id: str,
    model: str | None = None,
) -> tuple[str, list[ContentReference]]:
    """Add references to text and return the processed text with reference status.

    Returns:
        Tuple[str, list[Reference]]: (processed_text, ref_found)
    """
    references = _find_references(
        text=text,
        search_context=search_context,
        message_id=message_id,
    )

    # Only reference a source once, even if it is mentioned multiple times in the text.
    with_footnotes = _add_footnotes_to_text(text=text, references=references)

    # Gemini 2.5 flash model has tendency to add multiple references for the same fact
    # This is a workaround to limit the number of references to 5
    if model and model.startswith("litellm:gemini-2-5-flash"):
        reduced_text = _limit_consecutive_source_references(with_footnotes)

        # Get the references that remain after reduction
        remaining_numbers = set()
        sup_matches = re.findall(r"<sup>(\d+)</sup>", reduced_text)
        remaining_numbers = {int(match) for match in sup_matches}

        references = [
            ref for ref in references if ref.sequence_number in remaining_numbers
        ]
        text = _remove_hallucinated_references(reduced_text)
    else:
        text = _remove_hallucinated_references(with_footnotes)

    return text, references


def _preprocess_message(text: str) -> str:
    """Preprocess message text to normalize reference formats."""
    # Remove user & assistant references: XML format '[<user>]', '[\<user>]', etc.
    patterns = [
        (r"\[(\\)?(<)?user(>)?\]", ""),
        (r"\[(\\)?(<)?assistant(>)?\]", ""),
        (r"source[\s]?\[(\\)?(<)?conversation(>)?\]", "the previous conversation"),
        (r"\[(\\)?(<)?previous[_,\s]conversation(>)?\]", ""),
        (r"\[(\\)?(<)?past[_,\s]conversation(>)?\]", ""),
        (r"\[(\\)?(<)?previous[_,\s]?answer(>)?\]", ""),
        (r"\[(\\)?(<)?previous[_,\s]question(>)?\]", ""),
        (r"\[(\\)?(<)?conversation(>)?\]", ""),
        (r"\[(\\)?(<)?none(>)?\]", ""),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Replace XML format '[<source XX>]', '[<sourceXX>]' and '[\<sourceXX>]' with [XX]
    text = re.sub(r"\[(\\)?<source[\s]?(\d+)>\]", r"[\2]", text)

    # Replace format '[source XX]' and '[sourceXX]' with [XX]
    text = re.sub(r"\[source[\s]?(\d+)\]", r"[\1]", text)

    # Make all references non-bold
    text = re.sub(r"\[\*\*(\d+)\*\*\]", r"[\1]", text)

    # Replace 'SOURCEXX' and 'SOURCE XX' with [XX]
    text = re.sub(r"source[\s]?(\d+)", r"[\1]", text, flags=re.IGNORECASE)

    # Replace 'SOURCE n°X' with [XX]
    text = re.sub(r"source[\s]?n°(\d+)", r"[\1]", text, flags=re.IGNORECASE)

    # Replace '[<[XX]>]' and '[\<[XX]>]' with [XX]
    text = re.sub(r"\[(\\)?\[?<\[(\d+)\]?\]>\]", r"[\2]", text)

    # Replace '[[A], [B], ...]' or '[[A], B, C, ...]' with [A][B][C]...
    def replace_combined_brackets(match):
        numbers = re.findall(r"\d+", match.group(0))
        return "".join(f"[{n}]" for n in numbers)

    text = re.sub(
        r"\[\[(\d+)\](?:,\s*(?:\[)?\d+(?:\])?)*\]", replace_combined_brackets, text
    )

    return text


def _limit_consecutive_source_references(text: str) -> str:
    """Limit consecutive source references to maximum 5 unique sources."""

    def replace_consecutive(match):
        # Extract all numbers from the match and get unique values
        numbers = list(set(re.findall(r"\d+", match.group(0))))
        # Take only the first five unique numbers
        return "".join(f"<sup>{n}</sup>" for n in numbers[:5])

    # Find sequences of 5+ consecutive sources
    pattern = r"(?:<sup>\d+</sup>){5,}"
    return re.sub(pattern, replace_consecutive, text)


def _postprocess_message(text: str) -> str:
    """Format superscript references to remove duplicates."""

    def replace_sup_sequence(match):
        # Extract unique numbers from the entire match
        sup_numbers = set(re.findall(r"\d+", match.group(0)))
        return "".join(f"<sup>{n}</sup>" for n in sup_numbers)

    # Find sequences of 2+ superscripts including internal spaces
    pattern = r"(<sup>\d+</sup>[ ]*)+<sup>\d+</sup>"
    return re.sub(pattern, replace_sup_sequence, text)


def _get_max_sub_count_in_text(text: str) -> int:
    """Get the maximum superscript number in the text."""
    matches = re.findall(r"<sup>(\d+)</sup>", text)
    return max((int(match) for match in matches), default=0)


def _find_references(
    text: str,
    search_context: list[ContentChunk],
    message_id: str,
) -> list[ContentReference]:
    """Find references in text based on search context."""
    references: list[ContentReference] = []
    sequence_number = 1 + _get_max_sub_count_in_text(text)

    # Find all numbers in brackets to ensure we get references in order of occurrence
    numbers_in_brackets = _extract_numbers_in_brackets(text)

    for number in numbers_in_brackets:
        # Convert 1-based reference to 0-based index
        index = number - 1
        if index < 0 or index >= len(search_context):
            continue

        search = search_context[index]
        if not search:
            continue

        # Don't put the reference twice
        reference_name = search.title or search.key or f"Content {search.id}"
        found_reference = next(
            (r for r in references if r.name == reference_name), None
        )

        if found_reference:
            found_reference.original_index.append(number)
            continue

        url = (
            search.url
            if search.url and not search.internally_stored_at
            else f"unique://content/{search.id}"
        )

        references.append(
            ContentReference(
                name=reference_name,
                url=url,
                sequence_number=sequence_number,
                original_index=[number],
                source_id=f"{search.id}_{search.chunk_id}"
                if search.chunk_id
                else search.id,
                source="node-ingestion-chunks",
                message_id=message_id,
                id=search.id,
            )
        )
        sequence_number += 1

    return references


def _extract_numbers_in_brackets(text: str) -> list[int]:
    """Extract numbers from [X] format in text."""
    matches = re.findall(r"\[(\d+)\]", text)
    return [int(match) for match in matches]


def _add_footnotes_to_text(text: str, references: list[ContentReference]) -> str:
    """Replace bracket references with superscript footnotes."""
    for reference in references:
        for original_index in reference.original_index:
            text = text.replace(
                f"[{original_index}]", f"<sup>{reference.sequence_number}</sup>"
            )
    return text


def _remove_hallucinated_references(text: str) -> str:
    """Remove any remaining bracket references that weren't converted."""
    return re.sub(r"\[\d+\]", "", text).strip()
