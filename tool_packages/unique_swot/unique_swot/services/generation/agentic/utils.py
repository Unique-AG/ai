from unique_swot.utils import generate_unique_id


def create_map_from_list(*, prefix: str, items: list[str]) -> dict[str, str]:
    return {generate_unique_id(f"{prefix}_"): item for item in items}