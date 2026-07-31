"""Agentic Table (magic table) write commands for the Unique CLI.

The full-loop write slice over the public magic-table API (``2023-12-06``):

- ``create-sheet`` — create an empty sheet in a space.
- ``import`` — add questions/sources; adding new questions triggers the agent run.
- ``export`` — generate export artifacts (report / question export) and list them.

Together these let an agent build a sheet, run it, and collect the answers it
already reads with the Tier 0 commands in ``agentic_table.py``. Writes are the
first callers of the lifecycle mutations, so the write-path error mapping
(permission denied, sheet-processing, locked-row) lands here.

Each mutation is fire-and-forget by default; ``--wait`` opts into polling to
completion so a caller can chain the next step. Both waits have to tell the
result of *this* trigger apart from state left over from an earlier one, and
they do it differently because the evidence differs:

- Artifacts are durable records, so ``_wait_for_artifacts`` compares against a
  snapshot taken before the trigger and accepts only what is new.
- A run leaves no durable record, so ``_wait_for_run`` has to catch the sheet in
  ``PROCESSING`` — which a short run can pass through between two polls. Dense
  early polling narrows that window; only a per-run signal from the backend
  would close it (UN-23683).

The skill documents these alongside the read commands rather than gating them
behind a separate write skill: access varies per sheet, not per space, so a
skill-level toggle cannot express it. Authorization is enforced server-side on
every call, and the skill teaches the agent to attempt the operation and treat
a denial as information rather than as a failure to work around.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import NamedTuple, TypeVar

from unique_sdk._error import UniqueError
from unique_sdk.api_resources._agentic_table import (
    AgenticTable,
    AgenticTableSheetState,
    MagicTableActionResult,
    MagicTableArtifact,
    MagicTableArtifactState,
    MagicTableArtifactType,
)

# Reads and writes are one CLI group under one error prefix, so they share the
# prefix and the `is_error_output` predicate that goes with it, both of which
# live with the reads. Other command modules own a prefix each and define their
# own predicate; here a second copy would just be the same string twice.
from unique_sdk.cli.commands.agentic_table import AGENTIC_TABLE_ERROR_PREFIX
from unique_sdk.cli.formatting import (
    format_agentic_table_action_result,
    format_agentic_table_artifacts,
    format_agentic_table_created_sheet,
)
from unique_sdk.cli.state import ShellState

# Poll cadence and default budgets for the opt-in ``--wait`` flows. The run
# start window matches ``AgenticTableService.wait_for_run`` so the CLI and the
# toolkit agree on how long a pickup may take before it is treated as absent.
_POLL_INTERVAL_SECONDS = 5.0
_RUN_START_TIMEOUT_SECONDS = 120.0
_DEFAULT_WAIT_TIMEOUT_SECONDS = 600.0

# Sheet state is the only evidence that a run happened at all, and it is
# transient: a small sheet can be picked up and finished well inside one
# ``_POLL_INTERVAL_SECONDS``, leaving a completed run indistinguishable from one
# that never started. Sample densely over the window where a short run lives.
_FAST_POLL_INTERVAL_SECONDS = 1.0
_FAST_POLL_WINDOW_SECONDS = 20.0

# A poll is an idempotent read issued *after* the mutation has landed, so a
# blip on one request must not be reported as the write having failed.
_POLL_READ_ATTEMPTS = 3
_POLL_READ_BACKOFF_SECONDS = 1.0

_T = TypeVar("_T")


def _poll_interval(started_at: float, interval: float) -> float:
    """Poll densely at first, then settle to *interval*.

    A run is only visible while it is in flight, and a small sheet can be picked
    up and finished well inside one 5s interval — which looks identical to a run
    that never started. Sampling the opening seconds closely shrinks that blind
    spot without holding a ten-minute wait at a high request rate.
    """
    if time.monotonic() - started_at < _FAST_POLL_WINDOW_SECONDS:
        return min(_FAST_POLL_INTERVAL_SECONDS, interval)
    return interval


async def _poll_read(read: Callable[[], Awaitable[_T]]) -> _T:
    """Run one polling read, absorbing a transient failure.

    Polls happen after the mutation has already been accepted, so letting a
    single failed request end the wait would report a write that landed as an
    error. A 4xx is not retried: it is a decision rather than a blip, and it
    will read the same way on the next attempt.
    """
    for attempt in range(_POLL_READ_ATTEMPTS):
        try:
            return await read()
        except UniqueError as exc:
            client_error = exc.http_status is not None and 400 <= exc.http_status < 500
            if client_error or attempt == _POLL_READ_ATTEMPTS - 1:
                raise
            await asyncio.sleep(_POLL_READ_BACKOFF_SECONDS)
    raise AssertionError("unreachable: the loop either returns or raises")


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


def _rejected(result: MagicTableActionResult, *, action: str) -> str:
    """Render a soft backend rejection as a CLI error line.

    The lifecycle mutations report rejection in a 200 body (``status: false``)
    rather than an HTTP error, so it has to be mapped explicitly or the command
    would exit 0 and let an agent's ``&&`` chain continue — exporting stale
    answers after an import that never landed. ``AgenticTableService`` raises in
    the same situation.

    A body with no ``status`` field at all is a different case and says so: the
    request was not declined, it was unintelligible, and the mutation may well
    have been applied. Collapsing that into "rejected" would invite a retry.
    """
    if "status" not in result:
        return (
            f"{AGENTIC_TABLE_ERROR_PREFIX} {action} returned a response with no status "
            "field, so the outcome is unknown — it may have been applied. Check the "
            "sheet before retrying."
        )
    message = result.get("message") or "no detail returned"
    return f"{AGENTIC_TABLE_ERROR_PREFIX} {action} rejected: {message}"


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
    params: AgenticTable.CreateSheet = {"assistantId": assistant_id}
    if name is not None:
        params["name"] = name
    if due_at is not None:
        params["dueAt"] = due_at
    try:
        sheet = asyncio.run(
            AgenticTable.create_sheet(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                **params,
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
    start_timeout: float = _RUN_START_TIMEOUT_SECONDS,
    output_json: bool = False,
) -> str:
    """Import questions/sources into a sheet (``POST /magic-table/{id}/metadata``).

    Delta semantics: ids/texts already on the sheet are skipped, and the agent
    run is triggered only when *new* questions are added (sources alone do not
    trigger a run). The call is rejected with 422 while the sheet is already
    ``PROCESSING``, and with a ``status: false`` body when the backend declines
    it; either way the command fails rather than falling through to the wait.

    With ``wait``, polls the sheet state until the triggered run finishes (or
    ``timeout`` elapses) so the caller can chain an export.

    Whether an unobserved run is benign depends on what was submitted, so the
    two cases are kept apart rather than both reported as a note. A
    sources-only import never triggers a run, so nothing starting is the
    expected outcome and the command succeeds. When questions were submitted a
    run was expected, and not seeing one is indeterminate — the pickup may
    simply be late — so the command fails rather than letting a ``&&`` chain
    export a sheet that is still being answered. A re-import of questions the
    sheet already has lands here too: also a no-op, but not one this command
    can distinguish from a late pickup.

    ``start_timeout`` bounds how long a pickup may take before it is treated as
    absent; raise it when the worker queue is known to be slow, since a run that
    has not been picked up yet is not the same thing as a run that will not be.
    """
    params: AgenticTable.AddMetaData = {"tableId": table_id}
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
            **params,
        )
        if not result.get("status"):
            return _rejected(result, action="import")
        if output_json and not wait:
            return json.dumps({"result": result}, indent=2, default=str)
        if not wait:
            return format_agentic_table_action_result(result, action="import")

        started, final_state, timed_out = await _wait_for_run(
            state, table_id, timeout=timeout, start_timeout=start_timeout
        )
        if started and timed_out:
            return (
                f"{AGENTIC_TABLE_ERROR_PREFIX} timed out after {timeout:g}s waiting "
                f"for the run to finish (sheet {table_id} still PROCESSING)"
            )
        if not started and (question_file_ids or question_texts):
            window = min(start_timeout, timeout)
            return (
                f"{AGENTIC_TABLE_ERROR_PREFIX} imported questions into sheet "
                f"{table_id} but no run started within {window:g}s (state: "
                f"{final_state}); the questions are on the sheet and may still be "
                f"picked up, or may already have been answered. Poll get-sheet until "
                f"the state settles and the rows have answers before exporting — an "
                f"export now would report unanswered rows"
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

    Generation is asynchronous, so a ``status: false`` body means the trigger
    itself was declined and the command fails without polling. With ``wait``,
    polls ``list_artifacts`` until every requested type reaches ``DONE`` (or
    ``timeout``), then prints the artifact table with the ``contentId`` to
    download; an artifact entering ``ERROR`` fails fast. Without ``wait``,
    returns once generation is accepted.
    """
    # `click.Choice` already rejects an unknown type on the command line, but
    # this function is importable and the enum would raise a bare ValueError
    # past that guard — an exception where every other failure here is an
    # `agentic-table:` line the caller can test with `is_error_output`.
    allowed = {t.value for t in MagicTableArtifactType}
    unknown = [t for t in artifact_types if t not in allowed]
    if unknown:
        return (
            f"{AGENTIC_TABLE_ERROR_PREFIX} unknown artifact type: "
            f"{', '.join(unknown)} (expected: {', '.join(sorted(allowed))})"
        )
    wanted = [MagicTableArtifactType(t) for t in artifact_types]

    async def _run() -> str:
        since = (
            await _artifact_baseline(state, table_id, wanted)
            if wait
            else _ArtifactBaseline(ids=frozenset(), latest={})
        )
        result = await AgenticTable.generate_artifact(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            tableId=table_id,
            artifactTypes=wanted,
        )
        if not result.get("status"):
            return _rejected(result, action="export")
        if output_json and not wait:
            return json.dumps({"result": result}, indent=2, default=str)
        if not wait:
            return format_agentic_table_action_result(result, action="export")

        status, artifacts, missing = await _wait_for_artifacts(
            state, table_id, wanted, since=since, timeout=timeout
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

    The first phase is inherently lossy: ``PROCESSING`` is transient, so a run
    that finishes between two polls is indistinguishable from one that never
    began. Polling densely at the start (see ``_poll_interval``) narrows the gap
    but does not close it; closing it needs a durable per-run or per-row signal
    from the backend, which the public API does not expose yet (UN-23683).

    Returns ``(started, final_state, timed_out)``:
    - ``(False, last_state, False)`` — no run began within the start window.
    - ``(True, terminal_state, False)`` — the run started and finished.
    - ``(True, PROCESSING, True)`` — the run started but did not finish in time.
    """

    async def _state() -> AgenticTableSheetState:
        return await _poll_read(
            lambda: AgenticTable.get_sheet_state(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                tableId=table_id,
            )
        )

    began_at = time.monotonic()
    overall_deadline = began_at + timeout
    start_deadline = began_at + min(start_timeout, timeout)
    current = await _state()
    while current != AgenticTableSheetState.PROCESSING:
        if time.monotonic() >= start_deadline:
            return False, current, False
        await asyncio.sleep(_poll_interval(began_at, interval))
        current = await _state()

    while current == AgenticTableSheetState.PROCESSING:
        if time.monotonic() >= overall_deadline:
            return True, current, True
        await asyncio.sleep(_poll_interval(began_at, interval))
        current = await _state()
    return True, current, False


async def _list_artifacts(state: ShellState, table_id: str) -> list[MagicTableArtifact]:
    return await _poll_read(
        lambda: AgenticTable.list_artifacts(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            tableId=table_id,
        )
    )


class _ArtifactBaseline(NamedTuple):
    """What the sheet's artifacts looked like before a generation was triggered.

    ``ids`` are the records that already existed; ``latest`` is the newest
    ``updatedAt`` per requested type. Two signals rather than one because either
    can be absent: ``updatedAt`` is optional in the payload, and a record can be
    refreshed in place rather than replaced.
    """

    ids: frozenset[str]
    latest: dict[MagicTableArtifactType, str]


async def _artifact_baseline(
    state: ShellState,
    table_id: str,
    wanted_types: list[MagicTableArtifactType],
) -> _ArtifactBaseline:
    """Snapshot the artifacts of interest before triggering a generation.

    Taken up front so the wait can tell the resulting artifact apart from one
    left over from an earlier run.
    """
    wanted = set(wanted_types)
    artifacts = await _list_artifacts(state, table_id)
    ids: set[str] = set()
    latest: dict[MagicTableArtifactType, str] = {}
    for artifact in artifacts:
        artifact_type = artifact.get("artifactType")
        if artifact_type is None or artifact_type not in wanted:
            continue
        artifact_id = artifact.get("id")
        if artifact_id is not None:
            ids.add(artifact_id)
        updated_at = artifact.get("updatedAt") or ""
        if updated_at > latest.get(artifact_type, ""):
            latest[artifact_type] = updated_at
    return _ArtifactBaseline(ids=frozenset(ids), latest=latest)


def _is_fresh(artifact: MagicTableArtifact, baseline: _ArtifactBaseline) -> bool:
    """Whether *artifact* came out of the generation that was just triggered.

    Identity first: a record that did not exist before the trigger is new, which
    is how a finished report normally arrives — the backend stores it under its
    filename, as a separate row from the nameless ``IN_PROGRESS`` marker.

    ``updatedAt`` is the fallback, for a record refreshed in place. It has to be
    the fallback rather than the primary signal because it is optional in the
    payload: comparing two absent values would exclude the artifact on every
    poll and hang the wait on a generation that had in fact succeeded. The
    comparison is textual, which holds while the backend emits ISO-8601 in UTC
    at a fixed precision; if that ever changes, identity still carries the case.
    """
    artifact_id = artifact.get("id")
    if artifact_id is not None and artifact_id not in baseline.ids:
        return True
    artifact_type = artifact.get("artifactType")
    if artifact_type is None:
        return False
    updated_at = artifact.get("updatedAt") or ""
    return bool(updated_at) and updated_at > baseline.latest.get(artifact_type, "")


async def _wait_for_artifacts(
    state: ShellState,
    table_id: str,
    wanted_types: list[MagicTableArtifactType],
    *,
    since: _ArtifactBaseline,
    timeout: float,
    interval: float = _POLL_INTERVAL_SECONDS,
) -> tuple[str, list[MagicTableArtifact], list[str]]:
    """Poll ``list_artifacts`` until the requested types are freshly ``DONE``.

    ``since`` is the pre-trigger snapshot from ``_artifact_baseline``; an
    artifact counts only once ``_is_fresh`` recognises it, so a report left over
    from an earlier generation is never mistaken for this one.

    Freshness rather than an observed ``IN_PROGRESS`` phase is the signal
    deliberately. A sheet holds more than one artifact of a type — the trigger
    records its ``IN_PROGRESS`` marker under no name and the finished report is
    stored under its filename, so they are separate records and the marker is
    never updated to ``DONE``. Waiting to see the report itself turn
    ``IN_PROGRESS`` would also lose any generation that finishes inside one poll
    interval, which is the common case on a small sheet.

    Returns ``(status, artifacts, missing)`` where ``status`` is:
    - ``"done"`` — ``artifacts`` are the DONE records (one per requested type).
    - ``"error"`` — ``artifacts`` are the failed records.
    - ``"timeout"`` — ``missing`` lists the type values not yet DONE.
    """
    wanted = set(wanted_types)
    began_at = time.monotonic()
    deadline = began_at + timeout
    while True:
        artifacts = await _list_artifacts(state, table_id)
        done: dict[MagicTableArtifactType, MagicTableArtifact] = {}
        failed: list[MagicTableArtifact] = []
        for artifact in artifacts:
            artifact_type = artifact.get("artifactType")
            if artifact_type is None or artifact_type not in wanted:
                continue
            if not _is_fresh(artifact, since):
                continue
            artifact_state = artifact.get("artifactState")
            if artifact_state == MagicTableArtifactState.DONE:
                done[artifact_type] = artifact
            elif artifact_state == MagicTableArtifactState.ERROR:
                failed.append(artifact)
        if failed:
            return "error", failed, []
        if wanted <= set(done.keys()):
            return "done", [done[t] for t in wanted_types], []
        if time.monotonic() >= deadline:
            missing = sorted(str(t) for t in wanted - set(done.keys()))
            return "timeout", [], missing
        await asyncio.sleep(_poll_interval(began_at, interval))
