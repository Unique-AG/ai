# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unique-toolkit>=2026.22.0",
#   "unique-sdk>=2026.22.0",
# ]
# ///

from __future__ import annotations

from unique_toolkit.experimental.resources.content_folder import ContentFolder

folder_service = ContentFolder.from_settings()

DEMO_MULTI_A = "/EntangledToolkitDocs/MultiA"
DEMO_MULTI_B = "/EntangledToolkitDocs/MultiB"

created = folder_service.create(paths=[DEMO_MULTI_A, DEMO_MULTI_B])
for folder in created:
    print(folder.id, folder.name)
