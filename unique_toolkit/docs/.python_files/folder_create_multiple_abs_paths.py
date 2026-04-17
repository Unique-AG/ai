# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-main-multi>>[init]
# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-imports>>[init]
from __future__ import annotations

from unique_toolkit import ContentFolder
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-init>>[init]
folder_service = ContentFolder.from_settings()
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-constants-multi>>[init]
DEMO_MULTI_A = "/EntangledToolkitDocs/MultiA"
DEMO_MULTI_B = "/EntangledToolkitDocs/MultiB"
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-create-multi-paths>>[init]
created = folder_service.create_folder(paths=[DEMO_MULTI_A, DEMO_MULTI_B])
for folder in created:
    print(folder.id, folder.name)
# ~/~ end
# ~/~ end
