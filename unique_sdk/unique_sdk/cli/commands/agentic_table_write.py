"""Agentic Table (magic table) write commands for the Unique CLI.

The full-loop write slice over the public magic-table API (``2023-12-06``):

- ``create-sheet`` — create an empty sheet in a space.
- ``import`` — add questions/sources; adding new questions triggers the agent run.
- ``export`` — generate export artifacts (report / question export) and list them.

Together these let an agent build a sheet, run it, and collect the answers it
already reads with the Tier 0 commands in ``agentic_table.py``. Writes are the
first callers of the lifecycle mutations, so the write-path error mapping
(permission denied, sheet-processing, locked-row) lands here.

Each mutation is fire-and-forget by default; ``--wait`` opts into polling the
sheet/artifact state to completion so a caller can chain the next step. The
run/artifact polling mirrors ``AgenticTableService.wait_for_run`` /
``wait_for_artifacts``: it waits for the work to be observed *starting* before
accepting a terminal state, so a state left over from an earlier run is not
mistaken for the freshly triggered one.

These commands always exist in the binary; whether an agent is told about them
is controlled separately by the gated write skill (see UN-22200 / PR C).
"""

from __future__ import annotations

import asyncio
import json
import time

from unique_sdk._error import UniqueError
from unique_sdk.api_resources._agentic_table import (
    AgenticTable,
    AgenticTableSheetState,
    MagicTableArtifact,
    MagicTableArtifactState,
    MagicTableArtifactType,
)
from unique_sdk.cli.formatting import (
    format_agentic_table_action_result,
    format_agentic_table_artifacts,
    format_agentic_table_created_sheet,
)
from unique_sdk.cli.state import ShellState

AGENTIC_TABLE_ERROR_PREFIX = "agentic-table:"

# Poll cadence and default budgets for the opt-in ``--wait`` flows. The run
# start window is short: if a run has not begun by then the trigger almost
# certainly added no new questions (import is delta-based), which is reported
# rather than waited out for the full timeout.
_POLL_INTERVAL_SECONDS = 5.0
_RUN_START_TIMEOUT_SECONDS = 30.0
_DEFAULT_WAIT_TIMEOUT_SECONDS = 600.0


def is_error_output(output: str) -> bool:
    """Return ``True`` when *output* is an error message from an ``agentic-table`` write command."""
    return output.startswith(AGENTIC_TABLE_ERROR_PREFIX)


def _error(exc: UniqueError) -> str:
    """Render an SDK error as a CLI error line.

    A 403 (the platform's sheet-access guard) collapses to a stable
    ``permission denied`` so agent ``&&`` chains stop cleanly and no backend
    detail leaks. Other errors — including 422 while the sheet is ``PROCESSING``
    and locked-row rejections — pass through verbatim, since the backend message
    is already actionable.
    """
    if exc.http_status == 403:
        return f"{AGENTIC_TABLE_ERROR_PREFIX} permission denied"
    return f"{AGENTIC_TABLE_ERROR_PREFIX} {exc}"


def cmd_create_sheet(
    state: ShellState,
    assistant_id: str,
    *,
    name: str | None = None,
    due_at: str | None = None,
    output_json: bool = False,
) -> str:
    """Create a new sheet in a space (``POST /magic-table``).

    ``assistant_id`` is the space the sheet is created in; the caller must have
    write access to it. The returned ``sheetId`` is the ``table_id`` for every
    subsequent command.
    """
    params: dict[str, str] = {"assistantId": assistant_id}
    if name is not None:
        params["name"] = name
    if due_at is not None:
        params["dueAt"] = due_at
    try:
        sheet = asyncio.run(
            AgenticTable.create_sheet(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                **params,  # type: ignore[arg-type]
            )
        )
    except UniqueError as exc:
        return _error(exc)

    if output_json:
        return json.dumps(sheet, indent=2, default=str)
    return format_agentic_table_created_sheet(sheet)


def cmd_import(
    state: ShellState,
    table_id: str,
    *,
    question_file_ids: list[str] | None = None,
    question_texts: list[str] | None = None,
    source_file_ids: list[str] | None = None,
    context: str | None = None,
    wait: bool = False,
    timeout: float = _DEFAULT_WAIT_TIMEOUT_SECONDS,
    output_json: bool = False,
) -> str:
    """Import questions/sources into a sheet (``POST /magic-table/{id}/metadata``).

    Delta semantics: ids/texts already on the sheet are skipped, and the agent
    run is triggered only when *new* questions are added (sources alone do not
    trigger a run). The call is rejected with 422 while the sheet is already
    ``PROCESSING``.

    With ``wait``, polls the sheet state until the triggered run finishes (or
    ``timeout`` elapses) so the caller can chain an export. If no run starts
    within the start window (e.g. only sources were added), that is reported as
    a note rather than an error.
    """
    params: dict[str, object] = {"tableId": table_id}
    if question_file_ids:
        params["questionFileIds"] = question_file_ids
    if question_texts:
        params["questionTexts"] = question_texts
    if source_file_ids:
        params["sourceFileIds"] = source_file_ids
    if context is not None:
        params["context"] = context

    async def _run() -> str:
        result = await AgenticTable.add_metadata(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **params,  # type: ignore[arg-type]
        )
        if output_json and not wait:
            return json.dumps({"result": result}, indent=2, default=str)
        if not wait:
            return format_agentic_table_action_result(result, action="import")

        started, final_state, timed_out = await _wait_for_run(
            state, table_id, timeout=timeout
        )
        if started and timed_out:
            return (
                f"{AGENTIC_TABLE_ERROR_PREFIX} timed out after {timeout:g}s waiting "
                f"for the run to finish (sheet {table_id} still PROCESSING)"
            )
        if output_json:
            return json.dumps(
                {
                    "result": result,
                    "runStarted": started,
                    "finalState": str(final_state) if final_state else None,
                },
                indent=2,
                default=str,
            )
        note = (
            f"Run finished (state: {final_state})."
            if started
            else "No agent run started (import adds a run only for new questions)."
        )
        return f"{format_agentic_table_action_result(result, action='import')}\n{note}"

    try:
        return asyncio.run(_run())
    except UniqueError as exc:
        return _error(exc)


def cmd_export(
    state: ShellState,
    table_id: str,
    *,
    artifact_types: list[str],
    wait: bool = False,
    timeout: float = _DEFAULT_WAIT_TIMEOUT_SECONDS,
    output_json: bool = False,
) -> str:
    """Generate export artifacts for a sheet (``POST .../generate-artifact``).

    Generation is asynchronous. With ``wait``, polls ``list_artifacts`` until
    every requested type reaches ``DONE`` (or ``timeout``), then prints the
    artifact table with the ``contentId`` to download; an artifact entering
    ``ERROR`` fails fast. Without ``wait``, returns once generation is accepted.
    """
    wanted = [MagicTableArtifactType(t) for t in artifact_types]

    async def _run() -> str:
        result = await AgenticTable.generate_artifact(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            tableId=table_id,
            artifactTypes=wanted,
        )
        if output_json and not wait:
            return json.dumps({"result": result}, indent=2, default=str)
        if not wait:
            return format_agentic_table_action_result(result, action="export")

        status, artifacts, missing = await _wait_for_artifacts(
            state, table_id, wanted, timeout=timeout
        )
        if status == "error":
            failed = ", ".join(sorted(str(a.get("artifactType")) for a in artifacts))
            return (
                f"{AGENTIC_TABLE_ERROR_PREFIX} artifact generation failed for "
                f"{failed} on sheet {table_id}"
            )
        if status == "timeout":
            pending = ", ".join(missing)
            return (
                f"{AGENTIC_TABLE_ERROR_PREFIX} timed out after {timeout:g}s waiting "
                f"for exports ({pending}) on sheet {table_id}"
            )
        if output_json:
            return json.dumps(
                {"result": result, "artifacts": artifacts}, indent=2, default=str
            )
        return (
            f"{format_agentic_table_action_result(result, action='export')}\n"
            f"{format_agentic_table_artifacts(artifacts)}"
        )

    try:
        return asyncio.run(_run())
    except UniqueError as exc:
        return _error(exc)


async def _wait_for_run(
    state: ShellState,
    table_id: str,
    *,
    timeout: float,
    start_timeout: float = _RUN_START_TIMEOUT_SECONDS,
    interval: float = _POLL_INTERVAL_SECONDS,
) -> tuple[bool, AgenticTableSheetState | None, bool]:
    """Poll the sheet state through a triggered run.

    Two-phase, mirroring ``AgenticTableService.wait_for_run``: first wait for
    the sheet to enter ``PROCESSING`` (bounded by the shorter of ``start_timeout``
    and ``timeout``), then wait for it to leave ``PROCESSING``.

    Returns ``(started, final_state, timed_out)``:
    - ``(False, last_state, False)`` — no run began within the start window.
    - ``(True, terminal_state, False)`` — the run started and finished.
    - ``(True, PROCESSING, True)`` — the run started but did not finish in time.
    """

    async def _state() -> AgenticTableSheetState:
        return await AgenticTable.get_sheet_state(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            tableId=table_id,
        )

    overall_deadline = time.monotonic() + timeout
    start_deadline = time.monotonic() + min(start_timeout, timeout)
    current = await _state()
    while current != AgenticTableSheetState.PROCESSING:
        if time.monotonic() >= start_deadline:
            return False, current, False
        await asyncio.sleep(interval)
        current = await _state()

    while current == AgenticTableSheetState.PROCESSING:
        if time.monotonic() >= overall_deadline:
            return True, current, True
        await asyncio.sleep(interval)
        current = await _state()
    return True, current, False


async def _wait_for_artifacts(
    state: ShellState,
    table_id: str,
    wanted_types: list[MagicTableArtifactType],
    *,
    timeout: float,
    interval: float = _POLL_INTERVAL_SECONDS,
) -> tuple[str, list[MagicTableArtifact], list[str]]:
    """Poll ``list_artifacts`` until the requested types are ``DONE``.

    Mirrors ``AgenticTableService.wait_for_artifacts``: a terminal state is
    accepted for a type only after ``IN_PROGRESS`` has been observed for it, so
    an artifact left over from an earlier generation is not mistaken for the
    newly triggered one.

    Returns ``(status, artifacts, missing)`` where ``status`` is:
    - ``"done"`` — ``artifacts`` are the DONE records (one per requested type).
    - ``"error"`` — ``artifacts`` are the failed records.
    - ``"timeout"`` — ``missing`` lists the type values not yet DONE.
    """
    wanted = set(wanted_types)
    started: set[MagicTableArtifactType] = set()
    deadline = time.monotonic() + timeout
    while True:
        artifacts = await AgenticTable.list_artifacts(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            tableId=table_id,
        )
        current = {
            a["artifactType"]: a for a in artifacts if a.get("artifactType") in wanted
        }
        started.update(
            artifact_type
            for artifact_type, artifact in current.items()
            if artifact.get("artifactState") == MagicTableArtifactState.IN_PROGRESS
        )
        failed = [
            artifact
            for artifact_type, artifact in current.items()
            if artifact_type in started
            and artifact.get("artifactState") == MagicTableArtifactState.ERROR
        ]
        if failed:
            return "error", failed, []
        done = {
            artifact_type: artifact
            for artifact_type, artifact in current.items()
            if artifact_type in started
            and artifact.get("artifactState") == MagicTableArtifactState.DONE
        }
        if wanted <= set(done.keys()):
            return "done", [done[t] for t in wanted_types], []
        if time.monotonic() >= deadline:
            missing = sorted(str(t) for t in wanted - set(done.keys()))
            return "timeout", [], missing
        await asyncio.sleep(interval)
