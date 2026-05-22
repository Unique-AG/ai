from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

# Patterns that remove entire lines.
#
# NOTE on ordering: these patterns run *after* MarkdownTransform, so by the time
# they execute, ``[text](url)`` has already been collapsed to ``[text]`` and bare
# URLs are gone. That's what lets the "link-only / image-only / multi-bracket
# nav row" patterns below recognise the boilerplate Tavily ships back from
# directory-style sites (Hipflat, propertyhub, livinginsider, ddproperty…) —
# whole pages of currency dropdowns, BTS-station lists, and district-filter
# checkboxes that the agent never needs to see.
REGEX_LINE_REMOVAL_PATTERNS = [
    # ── Generic web boilerplate ─────────────────────────────────────────────
    # Skip navigation elements only (not content navigation)
    r"^[\*\+\-]?\s*(Skip to|Skip Navigation|Jump to|Accessibility help).*$",
    # Standalone authentication links (not part of content)
    r"^\s*(Sign In|Log In|Register|Sign Up|Create Account|My Account)\s*$",
    # Social media and newsletter signup buttons
    r"^[\?\[]?\s*(Subscribe|Follow Us|Share This|Newsletter Sign Up)\s*[\]?]?$",
    # Legal/Privacy footer elements (specific phrases)
    r"^.*(Cookie Policy|Privacy Policy|Terms of Service|Cookie Settings|Accept Cookies|Cookie Notice).*$",
    # Accessibility labels
    r"^\s*\[.*accessibility.*\].*$",
    # ── Structural nav (link/image-only lines, post-MarkdownTransform) ──────
    # One or more bracketed link tokens on a line, optionally prefixed by a
    # bullet/list marker. Catches ``* [Bangkok Home]``,
    # ``[Condo for Sale][Home for Sale][Townhome for Sale]`` (inline nav row),
    # and similar.
    r"^\s*[\*\+\-]?\s*(\[[^\]\n]+\]\s*){1,}$",
    # Pure image line: ``![alt]`` (after URL strip) with optional bullet.
    r"^\s*[\*\+\-]?\s*!\[[^\]\n]*\]\s*$",
    # Wrapped image-link form left over after MarkdownTransform: ``[![alt]]``.
    r"^\s*[\*\+\-]?\s*\[\s*!\[[^\]\n]*\]\s*\]\s*$",
    # Checkbox-style filter row with a short label (≤ 3 whitespace-separated
    # tokens). Targets the ``- [x] กรุงเทพฯ`` / ``- [x] BTS`` UI lists. The
    # short-label cap keeps real prose like ``- [x] this is a long sentence
    # about something important`` from getting eaten.
    r"^\s*[\*\+\-]\s*\[\s*[xX ]?\s*\]\s*\S+(\s+\S+){0,2}\s*$",
    # Currency / code dropdown row: short prose followed by a 3-letter code,
    # a dash, and a short symbol. Catches ``* Thai Baht THB - ฿``,
    # ``Swiss Franc CHF - CHF``, ``THB - ฿``, etc.
    r"^\s*\*?\s*[\w\s\-]{0,40}\b[A-Z]{3}\s+-\s+\S{1,5}\s*$",
]


class LineRemovalPatternsConfig(BaseModel):
    model_config = get_configuration_dict()
    enabled: bool = Field(
        default=True,
        title="Enable Line Removal",
        description="When enabled, automatically removes irrelevant lines from web pages such as navigation links, cookie notices, and sign-in buttons.",
    )
    patterns: list[str] = Field(
        default=REGEX_LINE_REMOVAL_PATTERNS,
        title="Removal Patterns",
        description="List of text patterns used to identify and remove irrelevant lines. Each pattern is a regular expression. Leave empty to skip line removal.",
    )


# Pattern/replacement pairs for content transformation
LINK_AND_URL_CLEANUP_PATTERNS = [
    # Transform markdown links: ``[text](url) → [text]``. Both groups allow
    # one level of nesting so the regex handles two common real-world forms
    # the previous ``[^\]]+/[^)]+`` pattern silently bailed on:
    #   1. wrapped image links ``[![alt](img-url)](page-url)``, where the
    #      bracket text itself contains ``[alt]``;
    #   2. ``javascript:void(0)``-style URLs with parens inside.
    # Either one left behind unmatched residue (``[![alt]](url)`` or
    # ``[text])``) that LineRemoval's bracket-only patterns couldn't see.
    (
        r"\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\((?:[^()]|\([^()]*\))*\)",
        r"[\1]",
    ),
    # Remove standalone URLs
    (r"https?://[^\s\])]+ ?", r""),
    # Normalize whitespace
    (r"\n{3,}", r"\n\n"),
    (r"[ \t]{2,}", r" "),
]


class CleaningConfig(BaseModel):
    model_config = get_configuration_dict()

    enable_character_sanitize: bool = Field(
        default=True,
        title="Enable Character Sanitization",
        description="When enabled, strips null bytes, control characters, and other non-text binary content from web page content.",
    )

    line_removal: LineRemovalPatternsConfig = Field(
        default_factory=LineRemovalPatternsConfig,
        title="Line Removal",
        description="Remove irrelevant lines from web pages, such as navigation menus, cookie banners, and sign-in buttons.",
    )

    enable_markdown_cleaning: bool = Field(
        default=True,
        title="Enable Link and URL Cleanup",
        description="When enabled, simplifies or removes web links and URLs from the content to improve readability.",
    )
