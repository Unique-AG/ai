"""Local end-to-end simulation of the UBP Agentic Table CLI flow (UN-22183 / R1).

Drives the full lifecycle through the new public API endpoints via the SDK/toolkit:

1. Create a sheet in a space            (POST /magic-table)
2. Tag it with sheet metadata           (POST /magic-table/{id}/sheet/metadata)
3. Import questions (and sources)       (POST /magic-table/{id}/metadata)
4. Wait for the agent run to finish     (poll GET /magic-table/{id})
5. Read back the answered sheet         (GET  /magic-table/{id})
6. Trigger an export                    (POST /magic-table/{id}/generate-artifact)
7. Wait for the artifact + report it    (poll GET /magic-table/{id}/artifacts)
8. Download the export file             (GET  /content/{contentId}/file)

Prerequisites (local dev):
- node-chat dev server on :8092
- agentic-table Python service on :5001
- an assistant with the RfpAgent module (see ASSISTANT_ID)

Run from the ai repo root:
    uv run python scripts/ubp_at_cli_e2e_simulation.py
"""

import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path

import unique_sdk
from unique_toolkit.agentic_table import (
    AgenticTableService,
    MagicTableArtifactType,
    SheetMetadataEntryInput,
)
from unique_toolkit.content.functions import download_content_to_bytes_async

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ubp-e2e")

# Local dev: node-chat trusts these headers directly (no gateway).
unique_sdk.api_key = os.environ.get("UNIQUE_API_KEY", "dummy")
unique_sdk.app_id = os.environ.get("UNIQUE_APP_ID", "dummy")
unique_sdk.api_base = os.environ.get("UNIQUE_API_BASE", "http://localhost:8092/public")

USER_ID = os.environ.get("UNIQUE_USER_ID", "361492024072929291")
COMPANY_ID = os.environ.get("UNIQUE_COMPANY_ID", "361492024072863755")
# "[Conduct] 2col" — most recently exercised local AT space. Override via env.
ASSISTANT_ID = os.environ.get(
    "UNIQUE_ASSISTANT_ID", "assistant_o9sl1scq1pfxfgunxyxyzg96"
)

QUESTION_TEXTS = [
    "What is the investment objective of the fund?",
    "Who is responsible for the portfolio management of the fund?",
]


async def main() -> int:
    log.info("Step 1: create sheet in space %s", ASSISTANT_ID)
    service = await AgenticTableService.create_sheet(
        user_id=USER_ID,
        company_id=COMPANY_ID,
        assistant_id=ASSISTANT_ID,
        name="UBP CLI e2e simulation",
    )
    assert service.created_sheet is not None
    log.info(
        "  -> sheetId=%s dueDiligenceId=%s state=%s chatId=%s",
        service.created_sheet.sheet_id,
        service.created_sheet.due_diligence_id,
        service.created_sheet.state,
        service.created_sheet.chat_id,
    )

    log.info("Step 2: tag sheet with metadata (client=UBP)")
    await service.create_sheet_metadata(
        [SheetMetadataEntryInput(key="client", value="UBP", exact_filter=True)]
    )
    metadata = await service.get_sheet_metadata()
    log.info("  -> sheet metadata: %s", [(m.key, m.value) for m in metadata])

    log.info("Step 3: import %d question texts", len(QUESTION_TEXTS))
    await service.import_questions_and_sources(question_texts=QUESTION_TEXTS)

    log.info("Step 4: wait for the agent run (two-phase poll)")
    final_state = await service.wait_for_run(
        start_timeout=120, completion_timeout=1800, poll_interval=5
    )
    log.info("  -> run finished, terminal state=%s", final_state)

    log.info("Step 5: read back the answered sheet")
    sheet = await service.get_sheet()
    rows: dict[int, dict[int, str]] = {}
    for cell in sheet.magic_table_cells:
        rows.setdefault(cell.row_order, {})[cell.column_order] = cell.text
    for row_order in sorted(rows):
        cells = rows[row_order]
        preview = {c: (t[:80] + "…" if len(t) > 80 else t) for c, t in cells.items()}
        log.info("  row %d: %s", row_order, preview)

    log.info("Step 6: trigger FULL_REPORT export")
    await service.generate_artifacts([MagicTableArtifactType.FULL_REPORT])

    log.info("Step 7: wait for the artifact to be DONE")
    artifacts = await service.wait_for_artifacts(
        [MagicTableArtifactType.FULL_REPORT], timeout=600, poll_interval=5
    )
    for artifact in artifacts:
        log.info(
            "  -> artifact id=%s type=%s state=%s contentId=%s name=%s mimeType=%s",
            artifact.id,
            artifact.artifact_type,
            artifact.artifact_state,
            artifact.content_id,
            artifact.name,
            artifact.mime_type,
        )

    log.info("Step 8: download the export file via the Content API")
    for artifact in artifacts:
        assert artifact.content_id is not None
        data = await download_content_to_bytes_async(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            content_id=artifact.content_id,
            chat_id=None,
        )
        out = Path(tempfile.gettempdir()) / (artifact.name or f"{artifact.id}.bin")
        out.write_bytes(data)
        log.info("  -> downloaded %d bytes to %s", len(data), out)

    log.info("E2E SIMULATION SUCCEEDED for sheet %s", service.table_id)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
