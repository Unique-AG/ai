# ~/~ begin <<docs/modules/examples/content/kb_service.md#kb-mirror-main>>[init]
# ~/~ begin <<docs/modules/examples/content/kb_service.md#kb-mirror-local-imports>>[init]
from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path

from unique_toolkit.content.folder import ContentFolder
from unique_toolkit.content.tree import ContentTree
from unique_toolkit.services.knowledge_base import KnowledgeBaseService
# ~/~ end


# ~/~ begin <<docs/modules/examples/content/kb_service.md#kb-mirror-local-mirror-fn>>[init]
def mirror_local_folder_to_kb(
    *,
    local_root: Path,
    kb_root_path: str,
    kb_service: KnowledgeBaseService,
    folder_service: ContentFolder,
) -> None:
    """Upload every file under *local_root*, preserving subfolders, without ingestion."""
    local_root = local_root.resolve()
    if not local_root.is_dir():
        msg = f"Not a directory: {local_root}"
        raise NotADirectoryError(msg)

    kb_prefix = kb_root_path if kb_root_path.startswith("/") else f"/{kb_root_path}"
    kb_prefix = kb_prefix.rstrip("/") or "/"

    scope_by_kb_dir: dict[str, str] = {}

    def scope_for_kb_dir(kb_dir: str) -> str:
        if kb_dir not in scope_by_kb_dir:
            created = folder_service.create_folder(path=kb_dir)
            scope_by_kb_dir[kb_dir] = created[-1].id
        return scope_by_kb_dir[kb_dir]

    _ = scope_for_kb_dir(kb_prefix)

    for file_path in sorted(p for p in local_root.rglob("*") if p.is_file()):
        rel = file_path.relative_to(local_root)
        parts = rel.parts
        parent_parts = parts[:-1]
        filename = parts[-1]
        kb_dir = kb_prefix + ("/" + "/".join(parent_parts) if parent_parts else "")
        scope_id = scope_for_kb_dir(kb_dir)
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        kb_service.upload_content(
            path_to_content=str(file_path),
            content_name=filename,
            mime_type=mime,
            scope_id=scope_id,
            skip_ingestion=True,
        )


# ~/~ end


# ~/~ begin <<docs/modules/examples/content/kb_service.md#kb-mirror-local-run>>[init]
async def _print_visible_tree() -> None:
    tree_svc = ContentTree.from_settings()
    print("=== Visible KB tree after mirror ===")
    print(await tree_svc.render_visible_tree_async(max_depth=None))


if __name__ == "__main__":
    LOCAL_ROOT = Path("./sample_tree").resolve()
    KB_ROOT = "/LocalMirror/MyProject"

    mirror_local_folder_to_kb(
        local_root=LOCAL_ROOT,
        kb_root_path=KB_ROOT,
        kb_service=KnowledgeBaseService.from_settings(),
        folder_service=ContentFolder.from_settings(),
    )

    asyncio.run(_print_visible_tree())
# ~/~ end
# ~/~ end
