# %%
import asyncio
import json
import time

from unique_toolkit import KnowledgeBaseService
from unique_toolkit.smart_rules.compile import Operator, Statement

kb_service = KnowledgeBaseService.from_settings()


# %%
async def main():

    # Resolve visible files (flat list of file names)
    start = time.perf_counter()
    visible_files = await kb_service.resolve_visible_files_async()
    elapsed = time.perf_counter() - start
    print(f"Visible files ({len(visible_files)} files, {elapsed:.2f}s):")
    for f in visible_files[:9]:
        print(f"  - {f}")
    if len(visible_files) > 9:
        print(f"  ... and {len(visible_files) - 9} more")

    # Resolve visible folder paths (flat list of folder paths)
    start = time.perf_counter()
    folder_paths = await kb_service.resolve_visible_folder_paths_async()
    elapsed = time.perf_counter() - start
    print(f"\nFolder paths ({len(folder_paths)} paths, {elapsed:.2f}s):")
    for p in folder_paths[:9]:
        print(f"  - {p}")
    if len(folder_paths) > 9:
        print(f"  ... and {len(folder_paths) - 9} more")

    # Resolve visible folder tree (hierarchical structure with files)
    start = time.perf_counter()
    folder_tree = await kb_service.resolve_visible_folder_tree_async()
    elapsed = time.perf_counter() - start
    tree_snippet = json.dumps(folder_tree, indent=2)[:500]
    print(f"\nFolder tree ({elapsed:.2f}s):\n{tree_snippet}\n...")

    # Resolve folder tree with a metadata filter (UniqueQL)
    rule = Statement(operator=Operator.EQUALS, value="application/pdf", path=["mimeType"])
    start = time.perf_counter()
    filtered_tree = await kb_service.resolve_visible_folder_tree_async(
        metadata_filter=rule.model_dump(mode="json")
    )
    elapsed = time.perf_counter() - start
    filtered_snippet = json.dumps(filtered_tree, indent=2)[:500]
    print(f"Filtered tree ({elapsed:.2f}s):\n{filtered_snippet}\n...")


asyncio.run(main())
