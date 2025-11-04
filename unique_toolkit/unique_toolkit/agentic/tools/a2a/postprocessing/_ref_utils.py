from typing import Callable, Iterable, Mapping, Sequence

from unique_toolkit._common.referencing import get_reference_pattern
from unique_toolkit._common.string_utilities import replace_in_text
from unique_toolkit.content import ContentReference

SourceId = str
SequenceNumber = int


def _add_source_ids(
    existing_refs: Mapping[SourceId, SequenceNumber],
    new_refs: Iterable[SourceId],
) -> dict[SourceId, SequenceNumber]:
    next_seq_num = max(existing_refs.values(), default=0) + 1
    new_seq_nums: dict[SourceId, SequenceNumber] = {}

    for source_id in new_refs:
        seq_num = existing_refs.get(source_id, None) or new_seq_nums.get(
            source_id, None
        )
        if seq_num is None:
            new_seq_nums[source_id] = next_seq_num
            next_seq_num += 1

    return new_seq_nums


def add_content_refs(
    message_refs: Sequence[ContentReference],
    new_refs: Sequence[ContentReference],
) -> list[ContentReference]:
    message_refs = list(message_refs)

    if len(new_refs) == 0:
        return message_refs

    existing_refs = {ref.source_id: ref.sequence_number for ref in message_refs}
    new_refs_by_source_id = {
        ref.source_id: ref for ref in sorted(new_refs, key=lambda x: x.sequence_number)
    }
    new_seq_nums = _add_source_ids(existing_refs, new_refs_by_source_id.keys())

    for source_id, seq_num in new_seq_nums.items():
        ref = new_refs_by_source_id[source_id]
        message_refs.append(
            ref.model_copy(update={"sequence_number": seq_num}, deep=True)
        )

    return message_refs


def add_content_refs_and_replace_in_text(
    message_text: str,
    message_refs: Sequence[ContentReference],
    new_refs: Sequence[ContentReference],
    ref_pattern_f: Callable[[int], str] = get_reference_pattern,
    ref_replacement_f: Callable[[int], str] = get_reference_pattern,
) -> tuple[str, list[ContentReference]]:
    if len(new_refs) == 0:
        return message_text, list(message_refs)

    references = add_content_refs(message_refs, new_refs)
    seq_num_for_source_id = {ref.source_id: ref.sequence_number for ref in references}
    ref_map = []

    for ref in new_refs:
        old_seq_num = ref.sequence_number
        new_seq_num = seq_num_for_source_id[ref.source_id]

        ref_map.append((ref_pattern_f(old_seq_num), ref_replacement_f(new_seq_num)))

    return replace_in_text(message_text, ref_map), references
