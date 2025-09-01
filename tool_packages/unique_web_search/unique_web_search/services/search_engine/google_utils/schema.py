from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit.history_manager.history_manager import DeactivatedNone
from unique_toolkit.tools.config import get_configuration_dict


class ImgColorType(StrEnum):
    COLOR = "color"
    GRAY = "gray"
    MONO = "mono"
    TRANS = "trans"


class ImgDominantColor(StrEnum):
    BLACK = "black"
    BLUE = "blue"
    BROWN = "brown"
    GRAY = "gray"
    GREEN = "green"
    ORANGE = "orange"
    PINK = "pink"
    PURPLE = "purple"
    RED = "red"
    TEAL = "teal"
    WHITE = "white"
    YELLOW = "yellow"


class ImgSize(StrEnum):
    HUGE = "huge"
    ICON = "icon"
    LARGE = "large"
    MEDIUM = "medium"
    SMALL = "small"
    XLARGE = "xlarge"
    XXLARGE = "xxlarge"


class ImgType(StrEnum):
    CLIPART = "clipart"
    FACE = "face"
    LINEART = "lineart"
    STOCK = "stock"
    PHOTO = "photo"
    ANIMATED = "animated"


class Safe(StrEnum):
    ACTIVE = "active"
    OFF = "off"


class SearchType(StrEnum):
    IMAGE = "image"


class SiteSearchFilter(StrEnum):
    EXCLUDE = "e"
    INCLUDE = "i"


class GoogleSearchQueryParams(BaseModel):
    """
    Required Google Custom Search API query parameters.
    Based on the official Google Custom Search JSON API documentation.
    """

    model_config = get_configuration_dict()

    q: str = Field(..., description="Query string")
    cx: str = Field(
        ...,
        description="The Programmable Search Engine ID to use for this request",
    )
    key: str = Field(..., description="API key for authentication")


class Rights(StrEnum):
    CC_PUBLICDOMAIN = "cc_publicdomain"
    CC_ATTRIBUTE = "cc_attribute"
    CC_SHAREALIKE = "cc_sharealike"
    CC_NONCOMMERCIAL = "cc_noncommercial"
    CC_NONDERIVED = "cc_nonderived"


class GoogleSearchOptionalQueryParams(BaseModel):
    """
    Optional Google Custom Search API query parameters.
    Based on the official Google Custom Search JSON API documentation.
    """

    model_config = get_configuration_dict()

    cx: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="The Programmable Search Engine ID to use for this request. If not provided, the default Programmable Search Engine ID will be used.",
    )

    c2coff: Annotated[Literal["0", "1"], Field(title="Active")] | DeactivatedNone = (
        Field(
            default=None,
            description="Enables or disables Simplified and Traditional Chinese Search. 0: Enabled (default), 1: Disabled",
        )
    )
    cr: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="Restricts search results to documents originating in a particular country",
    )
    date_restrict: SkipJsonSchema[str | None] = Field(
        default=None,
        alias="dateRestrict",
        description="Restricts results to URLs based on date. Examples: d[number], w[number], m[number], y[number]",
    )
    exact_terms: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        alias="exactTerms",
        description="Identifies a phrase that all documents in the search results must contain",
    )
    exclude_terms: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        alias="excludeTerms",
        description="Identifies a word or phrase that should not appear in any documents in the search results",
    )
    file_type: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        alias="fileType",
        description="Restricts results to files of a specified extension",
    )
    filter: Annotated[Literal["0", "1"], Field(title="Active")] | DeactivatedNone = (
        Field(
            default=None,
            description="Controls turning on or off the duplicate content filter. 0: Turns off, 1: Turns on",
        )
    )
    gl: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="Geolocation of end user. Two-letter country code",
    )
    high_range: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        alias="highRange",
        description="Specifies the ending value for a search range",
    )
    hl: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None, description="Sets the user interface language"
    )
    hq: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="Appends the specified query terms to the query, as if they were combined with a logical AND operator",
    )
    img_color_type: Annotated[ImgColorType, Field(title="Active")] | DeactivatedNone = (
        Field(
            default=None,
            alias="imgColorType",
            description="Returns black and white, grayscale, transparent, or color images",
        )
    )
    img_dominant_color: (
        Annotated[ImgDominantColor, Field(title="Active")] | DeactivatedNone
    ) = Field(
        default=None,
        alias="imgDominantColor",
        description="Returns images of a specific dominant color",
        exclude=True,
    )
    link_site: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        alias="linkSite",
        description="Specifies that all search results should contain a link to a particular URL",
    )
    low_range: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        alias="lowRange",
        description="Specifies the starting value for a search range",
    )
    lr: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="Restricts the search to documents written in a particular language (e.g., lr=lang_ja)",
    )
    num: SkipJsonSchema[int] = Field(
        default=10,
        ge=1,
        description="Number of search results to return. Valid values are integers between 1 and 10, inclusive. Default is 10",
    )
    or_terms: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        alias="orTerms",
        description="Provides additional search terms to check for in a document",
    )

    rights: Annotated[Rights, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="Filters based on licensing. Supported values include: cc_publicdomain, cc_attribute, cc_sharealike, cc_noncommercial, cc_nonderived",
    )
    safe: Annotated[Safe, Field(title="Active")] | DeactivatedNone = Field(
        default=Safe.ACTIVE, description="Search safety level"
    )
    search_type: Annotated[SearchType, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        alias="searchType",
        description="Specifies the search type: image. If unspecified, results are limited to webpages",
    )
    site_search: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        alias="siteSearch",
        description="Specifies a given site which should always be included or excluded from results",
    )
    site_search_filter: (
        Annotated[SiteSearchFilter, Field(title="Active")] | DeactivatedNone
    ) = Field(
        default=None,
        alias="siteSearchFilter",
        description="Controls whether to include or exclude results from the site named in the siteSearch parameter",
    )
    sort: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="The sort expression to apply to the results. Example value: date",
    )
    start: SkipJsonSchema[int] = Field(
        default=1,
        ge=1,
        description="The index of the first result to return. Note: The JSON API will never return more than 100 results",
        exclude=True,
    )

    @field_validator("gl", mode="before")
    def validate_gl(cls, value):
        if value is not None:
            return value.lower()
        return value
