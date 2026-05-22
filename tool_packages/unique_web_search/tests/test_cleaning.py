"""Tests for the content_processing cleaning pipeline.

Focus: the LineRemoval + MarkdownTransform ordering and the new boilerplate
patterns that strip navigation-only chunks (currency dropdowns, BTS-station
lists, district-filter checkboxes) before they reach the agent. Driven by the
Hipflat/livinginsider/propertyhub traces from the BNPP test set, where the
first 4-5 chunks per page were pure nav junk and the actual listings only
appeared at chunk 5+.
"""

from unittest.mock import Mock

import pytest

from unique_web_search.services.content_processing.cleaning import (
    LineRemoval,
    LineRemovalPatternsConfig,
    MarkdownTransform,
)
from unique_web_search.services.content_processing.config import (
    ContentProcessorConfig,
)
from unique_web_search.services.content_processing.service import (
    ContentProcessor,
)


def _line_removal() -> LineRemoval:
    """Default LineRemoval with the production pattern list."""
    return LineRemoval(config=LineRemovalPatternsConfig())


def _markdown_transform() -> MarkdownTransform:
    return MarkdownTransform(enabled=True)


def _clean_end_to_end(content: str) -> str:
    """Run MarkdownTransform + LineRemoval in production order on a string."""
    return _line_removal()(_markdown_transform()(content))


class TestLineRemovalDropsLinkOnlyBoilerplate:
    """The largest class of nav chatter: bullet/markdown link-only lines."""

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "line",
        [
            "* [Bangkok Home]",
            "* [Apartment building for rent Bangkok]",
            "- [Sukhumvit Condo for rent]",
            "+ [Condo near Chula]",
            "[Edit]",
            "[ลงทะเบียนนายหน้า]",
        ],
    )
    def test_drops_single_bracketed_link_line(self, line: str) -> None:
        assert _line_removal()(line) == ""

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "line",
        [
            "[Condo for Sale][Home for Sale][Townhome for Sale][Land for Sale]",
            "[Bangkok Home][Chiangmai Home][Phuket Home][Pattaya Home]",
            "[ลงทะเบียนนายหน้า][ลงประกาศ]",
        ],
    )
    def test_drops_multi_bracket_inline_nav_row(self, line: str) -> None:
        assert _line_removal()(line) == ""

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "line",
        [
            "* « First",  # plain text with no brackets — keep
            "* Item description with content",
            "Hello world [link] inside a sentence",
            "Section A: real content here",
            "[Reference 1]: see footnote at bottom of page",
        ],
    )
    def test_keeps_real_prose_with_optional_links(self, line: str) -> None:
        assert _line_removal()(line) == line


class TestLineRemovalDropsImageOnlyLines:
    @pytest.mark.ai
    @pytest.mark.parametrize(
        "line",
        [
            "![Image 1: Hipflat]",
            "* ![Image 4]",
            "![logo]",
            "- ![banner]",
        ],
    )
    def test_drops_image_only_line(self, line: str) -> None:
        assert _line_removal()(line) == ""

    @pytest.mark.ai
    def test_keeps_image_line_with_trailing_text(self) -> None:
        # The real ad row: ``* ![Image 4]Advertise here`` — has content after
        # the image so we *must* keep it (the agent can decide whether the ad
        # text matters; we're not in the business of filtering content).
        line = "* ![Image 4]Advertise here"
        assert _line_removal()(line) == line


class TestLineRemovalDropsCheckboxFilters:
    """Drop short-label checkbox UI; preserve real lists with longer entries."""

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "line",
        [
            "- [x] กรุงเทพฯ",
            "- [x] BTS",
            "- [ ] Bangkok",
            "- [x] Phuket Island",  # two tokens, still short
        ],
    )
    def test_drops_short_checkbox_label(self, line: str) -> None:
        assert _line_removal()(line) == ""

    @pytest.mark.ai
    def test_keeps_long_checkbox_label(self) -> None:
        # Looks like a checkbox but the label is a real sentence — keep it,
        # could be a real to-do or content snippet from a Markdown article.
        line = "- [x] this is a long sentence about something important"
        assert _line_removal()(line) == line


class TestLineRemovalDropsCurrencyDropdowns:
    @pytest.mark.ai
    @pytest.mark.parametrize(
        "line",
        [
            "* Thai Baht THB - ฿",
            "* Swiss Franc CHF - CHF",
            "* Vietnamese Dong VND - ₫",
            "* New Zealand Dollar NZD - $",
            "Thai Baht THB - ฿",
            "THB - ฿",
            "* USD - $",
        ],
    )
    def test_drops_currency_dropdown_row(self, line: str) -> None:
        assert _line_removal()(line) == ""

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "line",
        [
            "The BIS published a report on FX markets in Q3.",  # has 3-letter code but no "- $" pattern
            "Section A.B.C describes the methodology.",
            "Page 1 of 12 - next",  # not a currency code
        ],
    )
    def test_keeps_unrelated_prose_with_abbreviations(self, line: str) -> None:
        assert _line_removal()(line) == line


class TestMarkdownTransformThenLineRemoval:
    """End-to-end on the *exact* boilerplate shapes from the Hipflat trace.

    The whole point of reordering MarkdownTransform before LineRemoval is so
    that ``[text](url)`` collapses to ``[text]`` *first*, and LineRemoval's
    bracket-only patterns can then strip them out. Verify the integration.
    """

    @pytest.mark.ai
    def test_markdown_link_line_dropped_after_url_collapse(self) -> None:
        # Raw form from Tavily: a markdown link line.
        raw = "* [English - EN](javascript:void(0))"
        # MarkdownTransform → ``* [English - EN]`` → LineRemoval drops it.
        assert _clean_end_to_end(raw) == ""

    @pytest.mark.ai
    def test_wrapped_image_link_dropped(self) -> None:
        # The Hipflat header logo: ``[![Image 1: Hipflat]](/some/url)`` →
        # MarkdownTransform → ``[![Image 1: Hipflat]]`` → LineRemoval drops.
        raw = "[![Image 1: Hipflat]](/HIPFLAT)"
        assert _clean_end_to_end(raw) == ""

    @pytest.mark.ai
    def test_real_listing_content_survives(self) -> None:
        # The kind of line we actually want the agent to see — a real Hipflat
        # listing with size and price. Must survive cleaning.
        raw = (
            "ให้เช่า โกดัง 800 ตรม คลองเตย กรุงเทพมหานคร ฿ 152,000 / month "
            "พื้นที่ใช้สอย 800 ตร.ม."
        )
        assert _clean_end_to_end(raw) == raw

    @pytest.mark.ai
    def test_full_hipflat_header_collapses_to_almost_nothing(self) -> None:
        """The first chunk of a Hipflat page is ~80% nav. Verify cleaning."""
        raw = "\n".join(
            [
                "[![Image 1: Hipflat]](/HIPFLAT)",
                "* [English - EN](javascript:void(0))",
                "* [ภาษาไทย - TH](javascript:void(0))",
                "* Thai Baht THB - ฿",
                "* Euro EUR - €",
                "* United States Dollar USD - $",
                "- [x] กรุงเทพฯ",
                "- [x] ภูเก็ต",
                "[Condo for Sale][Home for Sale][Land for Sale]",
                "",
                "Khlong Toei warehouse 800 sqm available for ฿ 152,000/month.",
            ]
        )
        cleaned = _clean_end_to_end(raw)
        # Real content must survive.
        assert "152,000" in cleaned
        assert "Khlong Toei" in cleaned
        # None of the nav lines should survive.
        assert "Thai Baht" not in cleaned
        assert "Image 1" not in cleaned
        assert "Condo for Sale" not in cleaned
        assert "[ภาษาไทย" not in cleaned
        assert "กรุงเทพฯ" not in cleaned


class TestContentProcessorPipelineOrder:
    """Regression test for the cleaning_strategies ordering itself.

    If someone reorders the list back to the old form, MarkdownTransform won't
    run before LineRemoval and the new bracket-only patterns will see raw
    ``[text](url)`` markdown — which they don't match. Bake the ordering into
    a test so the regression is visible.
    """

    def _simple_encoder(self, text: str) -> list[int]:
        return list(range(len(text.split())))

    def _simple_decoder(self, tokens: list[int]) -> str:
        return " ".join(["word"] * len(tokens))

    @pytest.mark.ai
    def test_cleaning_strategies_order__markdown_before_line_removal(
        self,
    ) -> None:
        processor = ContentProcessor(
            language_model_service=Mock(),
            config=ContentProcessorConfig(),
            encoder=self._simple_encoder,
            decoder=self._simple_decoder,
        )
        names = [s.__class__.__name__ for s in processor._cleaning_strategies]
        # CharacterSanitize must remain first (NUL byte safety), then
        # MarkdownTransform must come *before* LineRemoval.
        assert names == ["CharacterSanitize", "MarkdownTransform", "LineRemoval"]
