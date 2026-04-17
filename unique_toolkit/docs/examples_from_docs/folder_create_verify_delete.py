# %%
from __future__ import annotations

from unique_toolkit.experimental.content_folder import ContentFolder

# Absolute path from the KB root; change if this collides with real data.
DEMO_FOLDER_PATH = "/EntangledToolkitDocsDemo"

folder_service = ContentFolder.from_settings()

created = folder_service.create_folder(path=DEMO_FOLDER_PATH)
leaf = created[-1]
print(f"Created folder id={leaf.id!r} name={leaf.name!r}")

info = folder_service.get_folder_info(scope_id=leaf.id)
print(
    f"Verified id={info.id!r} name={info.name!r} parent_id={info.parent_id!r} "
    f"(created as {DEMO_FOLDER_PATH!r}; compare in the UI)"
)
# Set a breakpoint here (IDE or `breakpoint()`) to inspect `info` and confirm in the UI.

delete_result = folder_service.delete_folder(scope_id=leaf.id)
print(
    "Deleted:",
    delete_result.get("successFolders"),
    "Failed:",
    delete_result.get("failedFolders"),
)
