from enum import StrEnum
from typing import Literal, TypeAlias

#: Markets Bing serves content for (``mkt``), in the documented order.
BingMarket: TypeAlias = Literal[
    "es-AR",
    "en-AU",
    "de-AT",
    "nl-BE",
    "fr-BE",
    "pt-BR",
    "en-CA",
    "fr-CA",
    "es-CL",
    "da-DK",
    "fi-FI",
    "fr-FR",
    "de-DE",
    "zh-HK",
    "en-IN",
    "en-ID",
    "it-IT",
    "ja-JP",
    "ko-KR",
    "en-MY",
    "es-MX",
    "nl-NL",
    "en-NZ",
    "no-NO",
    "zh-CN",
    "pl-PL",
    "en-PH",
    "ru-RU",
    "en-ZA",
    "es-ES",
    "sv-SE",
    "fr-CH",
    "de-CH",
    "zh-TW",
    "tr-TR",
    "en-GB",
    "en-US",
    "es-US",
]


class BingMarketSelection(StrEnum):
    """Admin market choices, including the deployment-default source."""

    DEFAULT = "Default"
    ES_AR = "es-AR"
    EN_AU = "en-AU"
    DE_AT = "de-AT"
    NL_BE = "nl-BE"
    FR_BE = "fr-BE"
    PT_BR = "pt-BR"
    EN_CA = "en-CA"
    FR_CA = "fr-CA"
    ES_CL = "es-CL"
    DA_DK = "da-DK"
    FI_FI = "fi-FI"
    FR_FR = "fr-FR"
    DE_DE = "de-DE"
    ZH_HK = "zh-HK"
    EN_IN = "en-IN"
    EN_ID = "en-ID"
    IT_IT = "it-IT"
    JA_JP = "ja-JP"
    KO_KR = "ko-KR"
    EN_MY = "en-MY"
    ES_MX = "es-MX"
    NL_NL = "nl-NL"
    EN_NZ = "en-NZ"
    NO_NO = "no-NO"
    ZH_CN = "zh-CN"
    PL_PL = "pl-PL"
    EN_PH = "en-PH"
    RU_RU = "ru-RU"
    EN_ZA = "en-ZA"
    ES_ES = "es-ES"
    SV_SE = "sv-SE"
    FR_CH = "fr-CH"
    DE_CH = "de-CH"
    ZH_TW = "zh-TW"
    TR_TR = "tr-TR"
    EN_GB = "en-GB"
    EN_US = "en-US"
    ES_US = "es-US"


#: Languages Bing localizes its interface strings into (``setLang``).
BingSetLang: TypeAlias = Literal[
    "ar",
    "eu",
    "bn",
    "bg",
    "ca",
    "zh-hans",
    "zh-hant",
    "hr",
    "cs",
    "da",
    "nl",
    "en",
    "en-gb",
    "et",
    "fi",
    "fr",
    "gl",
    "de",
    "gu",
    "he",
    "hi",
    "hu",
    "is",
    "it",
    "jp",
    "kn",
    "ko",
    "lv",
    "lt",
    "ms",
    "ml",
    "mr",
    "nb",
    "pl",
    "pt-br",
    "pt-pt",
    "pa",
    "ro",
    "ru",
    "sr",
    "sk",
    "sl",
    "es",
    "sv",
    "ta",
    "te",
    "th",
    "tr",
    "uk",
    "vi",
]

#: Named recency windows accepted by the Bing ``freshness`` knob.
BingFreshnessPreset: TypeAlias = Literal["Day", "Week", "Month"]
