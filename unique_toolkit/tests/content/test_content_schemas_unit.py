import pytest

from unique_toolkit.content.schemas import Content

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_content(**kwargs) -> Content:
    """Minimal Content with only the fields relevant to is_ingested."""
    defaults = {"id": "cont_abc", "key": "file.pdf"}
    return Content(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Content.is_ingested
# ---------------------------------------------------------------------------


@pytest.mark.ai
class TestContentIsIngested:
    def test__returns_default_default_if_unknown__when_applied_ingestion_config_is_none(
        self,
    ):
        """
        Purpose: Verify is_ingested returns the default default_if_unknown (True) when
                 applied_ingestion_config is None.
        Why this matters: Callers rely on the default to mean "assume ingested" when
                          no config metadata is present (e.g. legacy content).
        Setup summary: Content with applied_ingestion_config=None; assert True is returned.
        """
        content = make_content(applied_ingestion_config=None)

        assert content.is_ingested() is True

    @pytest.mark.parametrize("default_if_unknown", [True, False])
    def test__returns_custom_default_if_unknown__when_applied_ingestion_config_is_none(
        self, default_if_unknown: bool
    ):
        """
        Purpose: Verify is_ingested honours a caller-supplied default_if_unknown when
                 applied_ingestion_config is None.
        Why this matters: Some call sites need a conservative False default to avoid
                          treating missing config as "ingested".
        Setup summary: Content with applied_ingestion_config=None; parametrise
                       default_if_unknown; assert the exact value is echoed back.
        """
        content = make_content(applied_ingestion_config=None)

        assert (
            content.is_ingested(default_if_unknown=default_if_unknown)
            is default_if_unknown
        )

    def test__returns_default_default_if_unknown__when_uniqueIngestionMode_key_missing(
        self,
    ):
        """
        Purpose: Verify is_ingested returns the default default_if_unknown (True) when
                 applied_ingestion_config exists but lacks the uniqueIngestionMode key.
        Why this matters: A config dict that was populated with other keys but not the
                          mode key is functionally equivalent to "undefined" for this check.
        Setup summary: Content with a config dict that omits uniqueIngestionMode;
                       assert True is returned.
        """
        content = make_content(applied_ingestion_config={"chunkStrategy": "default"})

        assert content.is_ingested() is True

    @pytest.mark.parametrize("default_if_unknown", [True, False])
    def test__returns_custom_default_if_unknown__when_uniqueIngestionMode_key_missing(
        self, default_if_unknown: bool
    ):
        """
        Purpose: Verify is_ingested honours a caller-supplied default_if_unknown when the
                 uniqueIngestionMode key is absent from applied_ingestion_config.
        Why this matters: Consistent behaviour regardless of which "undefined" branch is hit.
        Setup summary: Config dict without uniqueIngestionMode; parametrise default_if_unknown;
                       assert the exact value is echoed back.
        """
        content = make_content(applied_ingestion_config={"chunkStrategy": "default"})

        assert (
            content.is_ingested(default_if_unknown=default_if_unknown)
            is default_if_unknown
        )

    def test__returns_false__when_uniqueIngestionMode_is_SKIP_INGESTION(self):
        """
        Purpose: Verify is_ingested returns False when uniqueIngestionMode is SKIP_INGESTION.
        Why this matters: SKIP_INGESTION signals that content was deliberately not ingested;
                          callers must not treat it as available for retrieval.
        Setup summary: Config with uniqueIngestionMode=SKIP_INGESTION; assert False.
        """
        content = make_content(
            applied_ingestion_config={"uniqueIngestionMode": "SKIP_INGESTION"}
        )

        assert content.is_ingested() is False

    def test__returns_false__when_uniqueIngestionMode_is_SKIP_EXCEL_INGESTION(self):
        """
        Purpose: Verify is_ingested returns False when uniqueIngestionMode is
                 SKIP_EXCEL_INGESTION.
        Why this matters: Excel files skipped during ingestion must not be treated
                          as searchable content.
        Setup summary: Config with uniqueIngestionMode=SKIP_EXCEL_INGESTION; assert False.
        """
        content = make_content(
            applied_ingestion_config={"uniqueIngestionMode": "SKIP_EXCEL_INGESTION"}
        )

        assert content.is_ingested() is False

    @pytest.mark.parametrize(
        "mode",
        [
            "STANDARD",
            "FULL",
            "CHUNKED",
            "some_future_mode",
        ],
    )
    def test__returns_true__when_uniqueIngestionMode_is_an_ingested_mode(
        self, mode: str
    ):
        """
        Purpose: Verify is_ingested returns True for any mode that is not in the
                 skip-list (SKIP_INGESTION, SKIP_EXCEL_INGESTION).
        Why this matters: New ingestion modes should be considered "ingested" by default
                          without requiring code changes.
        Setup summary: Parametrise over several non-skip mode strings; assert True for each.
        """
        content = make_content(applied_ingestion_config={"uniqueIngestionMode": mode})

        assert content.is_ingested() is True

    def test__default_if_unknown_arg_is_keyword_only(self):
        """
        Purpose: Verify that default_if_unknown cannot be passed as a positional argument.
        Why this matters: The method signature uses * to enforce keyword-only; passing
                          it positionally would be a caller error that Python should reject.
        Setup summary: Call is_ingested with a positional argument; assert TypeError raised.
        """
        content = make_content(applied_ingestion_config=None)

        with pytest.raises(TypeError):
            content.is_ingested(False)  # type: ignore[call-arg]
