from pydantic import BaseModel, Field, RootModel
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

# Patterns that remove entire lines
REGEX_LINE_REMOVAL_PATTERNS = [
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


class Transformation(BaseModel):
    model_config = get_configuration_dict()

    source: str = Field(
        default="",
        title="Find Pattern",
        description="The text pattern to search for in the content (regular expression).",
    )
    target: str = Field(
        default="",
        title="Replace With",
        description="The text to replace matched patterns with. Leave empty to remove matches entirely.",
    )


class Transformations(RootModel):
    root: list[Transformation]


# Pattern/replacement pairs for content transformation
default_transformations = [
    # Transform markdown links: [text](url) → [text]
    Transformation(source=r"\[([^\]]+)\]\([^)]+\)", target=r"[\1]"),
    # Remove standalone URLs
    Transformation(source=r"https?://[^\s\])]+ ?", target=""),
    # Normalize whitespace
    Transformation(source=r"\n{3,}", target="\n\n"),
    Transformation(source=r"[ \t]{2,}", target=" "),
]


class MarkdownTransformationConfig(BaseModel):
    model_config = get_configuration_dict()
    enabled: bool = Field(
        default=True,
        title="Enable Link and URL Cleanup",
        description="When enabled, simplifies or removes web links and URLs from the content to improve readability.",
    )
    transformations: Transformations = Field(
        default=Transformations(root=default_transformations),
        title="Cleanup Rules",
        description="Rules that define how links and URLs are simplified or removed. Each rule has a find pattern and a replacement.",
    )


class CleaningConfig(BaseModel):
    model_config = get_configuration_dict()

    line_removal: LineRemovalPatternsConfig = Field(
        default_factory=LineRemovalPatternsConfig,
        title="Line Removal",
        description="Remove irrelevant lines from web pages, such as navigation menus, cookie banners, and sign-in buttons.",
    )

    markdown_transformation: MarkdownTransformationConfig = Field(
        default_factory=MarkdownTransformationConfig,
        title="Link and URL Cleanup",
        description="Simplify or remove web links and URLs from the page content to improve readability.",
    )
