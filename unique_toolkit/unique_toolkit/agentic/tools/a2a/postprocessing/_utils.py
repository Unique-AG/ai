def _replace_references_in_text_non_overlapping(
    text: str, ref_map: dict[int, int]
) -> str:
    for orig, repl in ref_map.items():
        text = text.replace(f"<sup>{orig}</sup>", f"<sup>{repl}</sup>")
    return text


def _replace_references_in_text(text: str, ref_map: dict[int, int]) -> str:
    # 2 phase replacement, since the map keys and values can overlap
    max_ref = max(max(ref_map.keys(), default=0), max(ref_map.values(), default=0)) + 1
    unique_refs = range(max_ref, max_ref + len(ref_map))

    text = _replace_references_in_text_non_overlapping(
        text, dict(zip(ref_map.keys(), unique_refs))
    )
    return _replace_references_in_text_non_overlapping(
        text, dict(zip(unique_refs, ref_map.values()))
    )
