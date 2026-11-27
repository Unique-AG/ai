"""Tests for unique_user_memory Prometheus metrics wiring."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from prometheus_client import Counter, Histogram
from unique_toolkit.language_model.default_language_model import (
    DEFAULT_LANGUAGE_MODEL,
)
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.monitoring import get_metrics, metric_scope

from unique_user_memory import metrics as metrics_module
from unique_user_memory.config import UserMemoryConfig
from unique_user_memory.user_memory import (
    UserMemoryState,
    count_tokens,
    download_user_memory,
    fit_user_memory,
    load_user_memory,
    scrub_user_memory,
    should_consolidate_memory,
    upload_user_memory,
)
from unique_user_memory.user_memory_postprocessor import UserMemoryPostprocessor
from unique_user_memory.user_memory_prompts import empty_profile

_TEST_LANGUAGE_MODEL = LanguageModelInfo.from_name(DEFAULT_LANGUAGE_MODEL)


def _complete_profile_body(identity: str = "- Prefers concise answers") -> str:
    sections = (
        f"## Identity\n{identity}",
        "## Communication Preferences\n_(empty)_",
        "## Work Context\n_(empty)_",
        "## Skills & Expertise\n_(empty)_",
        "## Follow-ups\n_(empty)_",
        "## Recent Topics\n_(empty)_",
    )
    return "\n\n".join(sections)


def _count(counter: Counter, **labels: str) -> float:
    return counter.labels(**labels)._value.get()


def _hist_sum(histogram: Histogram, **labels: str) -> float:
    return histogram.labels(**labels)._sum.get()


@pytest.mark.ai
def test_metrics__exports_histograms_and_counters__for_instrumented_paths() -> None:
    """Purpose: Verify each declared metric is a Prometheus Histogram or Counter.
    Why this matters: A broken import or missing monitoring extra fails at runtime
    on every load and postprocessor run.
    Setup summary: Import the metrics module and assert types on representative instruments.
    """
    assert isinstance(metrics_module.load_duration, Histogram)
    assert isinstance(metrics_module.load_total, Counter)
    assert isinstance(metrics_module.postprocessor_duration, Histogram)
    assert isinstance(metrics_module.postprocessor_total, Counter)
    assert isinstance(metrics_module.errors, Counter)
    assert isinstance(metrics_module.llm_duration, Histogram)
    assert isinstance(metrics_module.llm_errors, Counter)
    assert isinstance(metrics_module.gate_decisions, Counter)
    assert isinstance(metrics_module.scrub_decisions, Counter)
    assert isinstance(metrics_module.consolidation_results, Counter)
    assert isinstance(metrics_module.storage_duration, Histogram)
    assert isinstance(metrics_module.storage_total, Counter)
    assert isinstance(metrics_module.memory_length_tokens, Histogram)
    assert isinstance(metrics_module.memory_length_chars, Histogram)
    assert isinstance(metrics_module.condense_total, Counter)


@pytest.mark.ai
def test_metrics__metric_scope__observes_duration_and_exposes_metrics() -> None:
    """Purpose: Confirm `metric_scope` works with package histograms/counters.
    Why this matters: LLM and storage stages rely on this context manager; a
    label mismatch would raise at runtime and hide the real error.
    Setup summary: Run a no-op block under metric_scope, then scan get_metrics().
    """
    with metric_scope(
        metrics_module.llm_duration,
        metrics_module.llm_errors,
        purpose="pytest_metrics",
        model="pytest-model",
    ):
        pass

    body = get_metrics()
    assert b"unique_user_memory_llm_duration_seconds" in body


@pytest.mark.ai
def test_metrics__observe_unlabeled__records_load_duration() -> None:
    """Purpose: Verify unlabeled histograms can be timed without calling labels().
    Why this matters: prometheus_client rejects labels() on instruments declared
    with an empty label set, so load/postprocessor timing cannot use metric_scope.
    Setup summary: Time a no-op with observe_unlabeled and check exposition.
    """
    with metrics_module.observe_unlabeled(metrics_module.load_duration):
        pass

    assert b"unique_user_memory_load_duration_seconds" in get_metrics()


@pytest.mark.ai
def test_metrics__metric_scope_llm_errors_on_exception__records_error_type_label() -> (
    None
):
    """Purpose: Ensure `llm_errors` declares `error_type` so metric_scope can increment.
    Why this matters: A label mismatch raises ValueError from prometheus_client.
    Setup summary: Raise inside metric_scope and assert exposition includes the labels.
    """
    with pytest.raises(RuntimeError, match="expected failure"):
        with metric_scope(
            metrics_module.llm_duration,
            metrics_module.llm_errors,
            purpose="pytest_llm_errors",
            model="pytest-model",
        ):
            raise RuntimeError("expected failure")

    body = get_metrics()
    assert b"unique_user_memory_llm_errors_total" in body
    assert b"pytest_llm_errors" in body
    assert b"pytest-model" in body
    assert b"RuntimeError" in body


@pytest.mark.ai
@pytest.mark.asyncio
async def test_metrics__gate_records_noop_and_fail_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: Verify the gate increments decision counters for NOOP and errors.
    Why this matters: The dashboard skip-rate and fail-open panels read these series.
    Setup summary: Run the gate once with NOOP and once with a raised LLM error.
    """
    noop_before = _count(metrics_module.gate_decisions, decision="noop")
    fail_before = _count(metrics_module.gate_decisions, decision="fail_open")
    error_before = _count(
        metrics_module.errors, stage="gate", error_type="RuntimeError"
    )

    response = MagicMock()
    response.choices[0].message.content = "NOOP"
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    await should_consolidate_memory(
        current_memory=empty_profile("user_1"),
        user_id="user_1",
        user_message="hello",
        assistant_message="hi",
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    llm_service.complete_async = AsyncMock(side_effect=RuntimeError("boom"))
    await should_consolidate_memory(
        current_memory=empty_profile("user_1"),
        user_id="user_1",
        user_message="hello",
        assistant_message="hi",
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert _count(metrics_module.gate_decisions, decision="noop") == noop_before + 1
    assert (
        _count(metrics_module.gate_decisions, decision="fail_open") == fail_before + 1
    )
    assert (
        _count(metrics_module.errors, stage="gate", error_type="RuntimeError")
        == error_before + 1
    )
    model = metrics_module.model_label(_TEST_LANGUAGE_MODEL.name)
    body = get_metrics()
    assert b"unique_user_memory_llm_duration_seconds" in body
    assert model.encode() in body
    assert b'purpose="gate"' in body


@pytest.mark.ai
@pytest.mark.asyncio
async def test_metrics__scrub_records_clean_cleaned_and_veto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: Verify the CID/PII scrub increments clean, cleaned, and veto.
    Why this matters: UN-24886 dashboards need a signal when the last gate
    strips content or blocks a write.
    Setup summary: Mock CLEAN, a cleaned profile, then an LLM error.
    """
    clean_before = _count(metrics_module.scrub_decisions, decision="clean")
    cleaned_before = _count(metrics_module.scrub_decisions, decision="cleaned")
    veto_before = _count(metrics_module.scrub_decisions, decision="veto")

    response = MagicMock()
    response.choices[0].message.content = "CLEAN"
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    await scrub_user_memory(
        body=_complete_profile_body(),
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    response.choices[0].message.content = _complete_profile_body(
        "- Runs quarterly portfolio reviews"
    )
    await scrub_user_memory(
        body=_complete_profile_body("- Reviews the portfolio of J. Muster"),
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    llm_service.complete_async = AsyncMock(side_effect=RuntimeError("boom"))
    await scrub_user_memory(
        body=_complete_profile_body(),
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert _count(metrics_module.scrub_decisions, decision="clean") == clean_before + 1
    assert (
        _count(metrics_module.scrub_decisions, decision="cleaned") == cleaned_before + 1
    )
    assert _count(metrics_module.scrub_decisions, decision="veto") == veto_before + 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_metrics__fit_records_condense_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: Verify over-budget fits increment condense_total by result.
    Why this matters: The hard-cut safety net should be visible when the LLM
    shrink fails or still exceeds the cap.
    Setup summary: Run fit once with a successful condense and once with None.
    """
    ok_before = _count(
        metrics_module.condense_total, trigger="condense", result="llm_ok"
    )
    failed_before = _count(
        metrics_module.condense_total,
        trigger="condense",
        result="llm_failed_then_hard_cut",
    )
    oversized = "# User Memory\n\n## Identity\n" + "\n".join(
        f"- fact number {index} that is fairly wordy about the user"
        for index in range(400)
    )

    monkeypatch.setattr(
        "unique_user_memory.user_memory.condense_user_memory",
        AsyncMock(return_value=_complete_profile_body("- concise summary of the user")),
    )
    await fit_user_memory(
        content=oversized,
        max_tokens=120,
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    monkeypatch.setattr(
        "unique_user_memory.user_memory.condense_user_memory",
        AsyncMock(return_value=None),
    )
    await fit_user_memory(
        content=oversized,
        max_tokens=120,
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert (
        _count(metrics_module.condense_total, trigger="condense", result="llm_ok")
        == ok_before + 1
    )
    assert (
        _count(
            metrics_module.condense_total,
            trigger="condense",
            result="llm_failed_then_hard_cut",
        )
        == failed_before + 1
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_metrics__load_records_skipped_and_folder_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: Verify load outcomes for missing ids and folder failure.
    Why this matters: Running without memory should show up as a first-class
    outcome, not look like a successful empty profile.
    Setup summary: Load with empty ids, then with a failed folder ensure.
    """
    skipped_before = _count(metrics_module.load_total, outcome="skipped_no_ids")
    folder_before = _count(metrics_module.load_total, outcome="folder_failed")

    skipped_event = MagicMock()
    skipped_event.user_id = ""
    skipped_event.company_id = "company_1"
    await load_user_memory(
        event=skipped_event,
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        logger=MagicMock(),
    )

    folder_event = MagicMock()
    folder_event.user_id = "user_1"
    folder_event.company_id = "company_1"
    monkeypatch.setattr(
        "unique_user_memory.user_memory.ensure_user_memory_folder",
        AsyncMock(return_value=None),
    )
    await load_user_memory(
        event=folder_event,
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        logger=MagicMock(),
    )

    assert (
        _count(metrics_module.load_total, outcome="skipped_no_ids")
        == skipped_before + 1
    )
    assert (
        _count(metrics_module.load_total, outcome="folder_failed") == folder_before + 1
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_metrics__load_records_memory_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: Verify load observes token and character length of the profile.
    Why this matters: The dashboard needs profile size, not only whether load
    succeeded, to see how full memory is versus the token cap.
    Setup summary: Load a short profile and assert both length histograms record.
    """
    profile = _complete_profile_body()
    expected_tokens = count_tokens(content=profile, language_model=_TEST_LANGUAGE_MODEL)
    tokens_before = _hist_sum(metrics_module.memory_length_tokens, phase="load")
    chars_before = _hist_sum(metrics_module.memory_length_chars, phase="load")
    monkeypatch.setattr(
        "unique_user_memory.user_memory.ensure_user_memory_folder",
        AsyncMock(return_value="scope_1"),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.download_user_memory",
        AsyncMock(return_value=profile),
    )

    event = MagicMock()
    event.user_id = "user_1"
    event.company_id = "company_1"
    state = await load_user_memory(
        event=event,
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        logger=MagicMock(),
    )

    assert state is not None
    assert state.text == profile
    assert (
        _hist_sum(metrics_module.memory_length_tokens, phase="load")
        == tokens_before + expected_tokens
    )
    assert _hist_sum(
        metrics_module.memory_length_chars, phase="load"
    ) == chars_before + len(profile)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_metrics__storage_records_download_not_found_and_upload_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: Verify storage counters for a missing memory file and a failed upload.
    Why this matters: First-turn empty downloads and upload failures must not
    be indistinguishable from successes on the dashboard.
    Setup summary: List contents without memory.md, then make upload raise.
    """
    missing_before = _count(
        metrics_module.storage_total, op="download", outcome="not_found"
    )
    upload_error_before = _count(
        metrics_module.storage_total, op="upload", outcome="error"
    )

    monkeypatch.setattr(
        "unique_user_memory.user_memory.search_contents_async",
        AsyncMock(return_value=[]),
    )
    text = await download_user_memory(
        scope_id="scope_1",
        user_id="user_1",
        company_id="company_1",
        logger=MagicMock(),
    )
    assert text == ""

    monkeypatch.setattr(
        "unique_user_memory.user_memory.upload_content_from_bytes_async",
        AsyncMock(side_effect=RuntimeError("store down")),
    )
    uploaded = await upload_user_memory(
        scope_id="scope_1",
        content=_complete_profile_body(),
        user_id="user_1",
        company_id="company_1",
        logger=MagicMock(),
    )
    assert uploaded is False

    assert (
        _count(metrics_module.storage_total, op="download", outcome="not_found")
        == missing_before + 1
    )
    assert (
        _count(metrics_module.storage_total, op="upload", outcome="error")
        == upload_error_before + 1
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_metrics__postprocessor_records_updated_and_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: Verify the postprocessor outcome counter for update vs NOOP.
    Why this matters: The top-row write-success panel is this series.
    Setup summary: Run once with a changed profile and successful upload, then
    once with an unchanged profile.
    """
    updated_before = _count(metrics_module.postprocessor_total, outcome="updated")
    noop_before = _count(metrics_module.postprocessor_total, outcome="noop")

    existing = empty_profile("user_1")
    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.consolidate_user_memory",
        AsyncMock(return_value=_complete_profile_body("- Updated")),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.upload_user_memory",
        AsyncMock(return_value=True),
    )
    event = MagicMock()
    event.user_id = "user_1"
    event.company_id = "company_1"
    event.payload.user_message.text = "remember this"
    loop_response = MagicMock()
    loop_response.message.text = "noted"
    postprocessor = UserMemoryPostprocessor(
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=event,
        state=UserMemoryState(scope_id="scope_1", text=existing),
        logger=MagicMock(),
        message_step_logger=MagicMock(
            log_updating_start=AsyncMock(),
            log_updating_complete=AsyncMock(),
        ),
    )
    assert await postprocessor.run(loop_response) is True

    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.consolidate_user_memory",
        AsyncMock(return_value=existing),
    )
    assert await postprocessor.run(loop_response) is False

    assert (
        _count(metrics_module.postprocessor_total, outcome="updated")
        == updated_before + 1
    )
    assert _count(metrics_module.postprocessor_total, outcome="noop") == noop_before + 1
