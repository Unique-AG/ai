"""Local e2e simulation of the UBP flow with an uploaded questionnaire file (UN-22183 / R1).

Variant of ``ubp_at_cli_e2e_simulation.py`` that mirrors UBP's real usage: instead of
inline question texts, a questionnaire DOCX is uploaded to the sheet's chat, we wait
for ingestion to finish, and import it via ``questionFileIds`` so the agent extracts
the questions itself. This is the upload -> wait-ingestion -> create -> import
composite from the design doc (Decision 5), done client-side.

Run from the ai repo root:
    UNIQUE_API_BASE="http://localhost:18092/public" \
        uv run python scripts/ubp_at_cli_e2e_question_file.py /path/to/questionnaire.docx
"""

import asyncio
import logging
import mimetypes
import os
import sys
import tempfile
import time
from pathlib import Path

import unique_sdk
from unique_toolkit.agentic_table import (
    AgenticTableService,
    MagicTableArtifactType,
)
from unique_toolkit.content.functions import (
    download_content_to_bytes_async,
    search_contents_async,
    upload_content_from_bytes_async,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("unique_sdk").setLevel(logging.WARNING)
log = logging.getLogger("ubp-e2e-qfile")

unique_sdk.api_key = os.environ.get("UNIQUE_API_KEY", "dummy")
unique_sdk.app_id = os.environ.get("UNIQUE_APP_ID", "dummy")
unique_sdk.api_base = os.environ.get("UNIQUE_API_BASE", "http://localhost:8092/public")

USER_ID = os.environ.get("UNIQUE_USER_ID", "361492024072929291")
COMPANY_ID = os.environ.get("UNIQUE_COMPANY_ID", "361492024072863755")
ASSISTANT_ID = os.environ.get(
    "UNIQUE_ASSISTANT_ID", "assistant_o9sl1scq1pfxfgunxyxyzg96"
)


async def wait_for_ingestion(
    content_id: str,
    chat_id: str | None,
    timeout: float = 300.0,
    poll_interval: float = 5.0,
) -> None:
    """Poll the Content API until the uploaded file's ingestion state is FINISHED."""
    deadline = time.monotonic() + timeout
    while True:
        contents = await search_contents_async(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            chat_id=chat_id,
            where={"id": {"equals": content_id}},
            include_failed_content=True,
        )
        state = contents[0].ingestion_state if contents else None
        if state == "FINISHED":
            return
        if state == "FAILED":
            raise RuntimeError(f"Ingestion failed for content {content_id}")
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Content {content_id} not ingested within {timeout}s (state={state})"
            )
        log.info("  ... ingestion state=%s, waiting", state)
        await asyncio.sleep(poll_interval)


async def main(questionnaire_path: Path) -> int:
    log.info("Step 1: create sheet in space %s", ASSISTANT_ID)
    service = await AgenticTableService.create_sheet(
        user_id=USER_ID,
        company_id=COMPANY_ID,
        assistant_id=ASSISTANT_ID,
        name=f"UBP CLI e2e - {questionnaire_path.stem}"[:80],
    )
    created = service.created_sheet
    assert created is not None
    log.info(
        "  -> sheetId=%s dueDiligenceId=%s chatId=%s",
        created.sheet_id,
        created.due_diligence_id,
        created.chat_id,
    )

    log.info(
        "Step 2: upload questionnaire '%s' to the sheet's chat", questionnaire_path.name
    )
    mime_type = (
        mimetypes.guess_type(questionnaire_path.name)[0] or "application/octet-stream"
    )
    content = await upload_content_from_bytes_async(
        user_id=USER_ID,
        company_id=COMPANY_ID,
        content=questionnaire_path.read_bytes(),
        content_name=questionnaire_path.name,
        mime_type=mime_type,
        chat_id=created.chat_id,
    )
    log.info("  -> contentId=%s mimeType=%s", content.id, mime_type)

    log.info("Step 3: wait for ingestion to finish")
    await wait_for_ingestion(content.id, created.chat_id)
    log.info("  -> ingestion FINISHED")

    log.info("Step 4: import the question file (agent extracts questions)")
    await service.import_questions_and_sources(question_file_ids=[content.id])

    log.info("Step 5: wait for the agent run (extraction + answering)")
    final_state = await service.wait_for_run(
        start_timeout=180, completion_timeout=3600, poll_interval=10
    )
    log.info("  -> run finished, terminal state=%s", final_state)

    log.info("Step 6: read back the answered sheet")
    sheet = await service.get_sheet()
    rows: dict[int, dict[int, str]] = {}
    for cell in sheet.magic_table_cells:
        rows.setdefault(cell.row_order, {})[cell.column_order] = cell.text
    log.info("  -> %d rows (incl. header)", len(rows))
    for row_order in sorted(rows)[:12]:
        cells = rows[row_order]
        preview = {c: (t[:70] + "…" if len(t) > 70 else t) for c, t in cells.items()}
        log.info("  row %d: %s", row_order, preview)

    log.info("Step 7: trigger FULL_REPORT export and wait")
    await service.generate_artifacts([MagicTableArtifactType.FULL_REPORT])
    artifacts = await service.wait_for_artifacts(
        [MagicTableArtifactType.FULL_REPORT], timeout=600, poll_interval=5
    )

    log.info("Step 8: download the export")
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

    log.info("E2E QUESTION-FILE SIMULATION SUCCEEDED for sheet %s", service.table_id)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} /path/to/questionnaire.docx", file=sys.stderr)
        sys.exit(2)
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(path)))
