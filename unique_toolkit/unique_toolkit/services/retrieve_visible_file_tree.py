import asyncio
import logging
from typing import Any

from unique_toolkit import KnowledgeBaseService
from unique_toolkit.content.schemas import ContentInfo

_LOGGER = logging.getLogger(__name__)


async def translate_scope_id_to_folder_name_async(
    knowledge_base_service: KnowledgeBaseService, *, scope_id: str
) -> str | None:
    try:
        folder_info = await knowledge_base_service.get_folder_info_async(
            scope_id=scope_id
        )
        return folder_info.name
    except Exception as e:
        _LOGGER.warning(f"Could not resolve folder for scope_id {scope_id}", exc_info=e)
        return None


async def translate_scope_ids_to_folder_name_async(
    knowledge_base_service: KnowledgeBaseService,
    *,
    scope_ids: set[str],
    max_concurrent_requests: int = 25,
) -> dict[str, str]:
    scope_id_list = list(scope_ids)
    semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def _resolve(sid: str) -> str | None:
        async with semaphore:
            return await translate_scope_id_to_folder_name_async(
                knowledge_base_service, scope_id=sid
            )

    results = await asyncio.gather(*[_resolve(sid) for sid in scope_id_list])

    return {
        key: value for key, value in zip(scope_id_list, results) if value is not None
    }


def extract_scope_ids(content_infos: list[ContentInfo]) -> set[str]:
    """
    Extracts all unique scope IDs from the ``folderIdPath`` metadata field
    across the given content infos.
    """
    scope_ids: set[str] = set()
    for content_info in content_infos:
        metadata = content_info.metadata
        if (
            metadata
            and (folder_id_path := metadata.get("folderIdPath")) is not None
            and isinstance(folder_id_path, str)
        ):
            for sid in folder_id_path.replace("uniquepathid://", "").split("/"):
                if sid:
                    scope_ids.add(sid)
    return scope_ids


async def resolve_visible_file_paths_async(
    knowledge_base_service: KnowledgeBaseService,
    *,
    metadata_filter: dict[str, Any] | None = None,
) -> list[list[str]]:
    """
    Resolves file paths visible to the current user, returning each as a list
    of path segments (folder names followed by the file name).

    E.g. ``[["Documents", "Reports", "report.pdf"], ["Images", "photo.jpg"]]``

    Args:
        knowledge_base_service: The KnowledgeBaseService instance.
        metadata_filter: Optional metadata filter to narrow the content scope.

    Returns:
        list[list[str]]: Each inner list is [folder1, folder2, ..., filename].
    """

    content_infos: list[
        ContentInfo
    ] = await knowledge_base_service.get_content_infos_async(
        metadata_filter=metadata_filter
    )

    scope_ids = extract_scope_ids(content_infos)
    scope_id_to_folder_name = await translate_scope_ids_to_folder_name_async(
        knowledge_base_service, scope_ids=scope_ids
    )
    folder_name_list_of_paths: list[list[str]] = []

    for content_info in content_infos:
        metadata = content_info.metadata

        folder_name_list = []
        # {FullPath} is present when documents are ingested via Confluence connector.
        if metadata and (full_path := metadata.get(r"{FullPath}")) is not None:
            folder_name_list = str(full_path).split("/")

        elif (
            metadata
            and (folder_id_path := metadata.get("folderIdPath")) is not None
            and isinstance(folder_id_path, str)
        ):
            scope_ids_list = [
                sid
                for sid in folder_id_path.replace("uniquepathid://", "").split("/")
                if sid
            ]

            folder_name_list = [
                scope_id_to_folder_name.get(scope_id, scope_id)
                for scope_id in scope_ids_list
            ]
        else:
            folder_name_list = ["_no_folder_path"]

        folder_name_list.append(content_info.key)
        folder_name_list_of_paths.append(folder_name_list)

    return folder_name_list_of_paths


def display_path_tree(paths: list[list[str]], root_name: str = ".") -> str:
    """
    Display a list of path lists as a tree (like the Linux `tree` command).

    Each sublist represents a path of folder names from root to leaf.
    Paths are merged into a shared tree structure and printed with
    unicode box-drawing characters (├──, └──, │).

    Args:
        paths: List of path lists, e.g. [["a", "b"], ["a", "c"], ["d"]]
        root_name: Name to show for the root node. Defaults to ".".

    Returns:
        String representation of the tree.

    Example:
        >>> display_path_tree([["docs", "api"], ["docs", "guides"], ["src"]])
        .
        ├── docs
        │   ├── api
        │   └── guides
        └── src
    """
    if not paths:
        return root_name

    # Build tree as nested dict: {name: {children...}}
    tree: dict[str, dict] = {}
    for path in paths:
        if not path:
            continue
        current = tree
        for segment in path:
            if segment:  # skip empty strings
                current = current.setdefault(segment, {})

    def _render(node: dict, prefix: str = "") -> list[str]:
        lines: list[str] = []
        folders = sorted(k for k in node if node[k])
        files = sorted(k for k in node if not node[k])
        children = folders + files
        for i, name in enumerate(children):
            last = i == len(children) - 1
            connector = "└── " if last else "├── "
            lines.append(prefix + connector + name)
            child_prefix = prefix + ("    " if last else "│   ")
            lines.extend(_render(node[name], child_prefix))
        return lines

    lines = [root_name] + _render(tree)
    return "\n".join(lines)
