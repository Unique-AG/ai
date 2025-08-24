from datetime import date
from enum import StrEnum

from pydantic import Field

from unique_stock_ticker.clients.six.schema import (
    BaseAPIModel,
    BaseResponsePayload,
    ContractType,
    ContractUnitType,
    CurrentCouponType,
    ExerciseType,
    InstrumentStatus,
    InstrumentType,
    InstrumentUnitType,
    Language,
    MaturityType,
    OptionType,
    SecurityType,
)


class InstrumentMatchingDescription(StrEnum):
    ISIN = "ISIN"
    VALOR = "VALOR"
    SEDOL = "SEDOL"
    WKN = "WKN"
    CUSIP = "CUSIP"
    SICOVAM = "SICOVAM"
    AUSTRIAN_NUMBER = "AUSTRIAN_NUMBER"
    BELGIAN_NUMBER = "BELGIAN_NUMBER"
    DANISH_NUMBER = "DANISH_NUMBER"
    FRENCH_RGA_CODE = "FRENCH_RGA_CODE"
    HONG_KONG_ISSUE_NUMBER = "HONG_KONG_ISSUE_NUMBER"
    ITALIAN_NUMBER = "ITALIAN_NUMBER"
    JAPANESE_ISSUE_CODE = "JAPANESE_ISSUE_CODE"
    JAPANESE_NEW_SECURITIES_CODE = "JAPANESE_NEW_SECURITIES_CODE"
    SOUTH_KOREAN_NUMBER = "SOUTH_KOREAN_NUMBER"
    LUXEMBOURG_NUMBER = "LUXEMBOURG_NUMBER"
    DUTCH_NUMBER = "DUTCH_NUMBER"
    NORWEGIAN_NUMBER = "NORWEGIAN_NUMBER"
    PORTUGUESE_NUMBER = "PORTUGUESE_NUMBER"
    SWEDISH_NUMBER = "SWEDISH_NUMBER"
    FIGI = "FIGI"
    FIGI_COMPOSITE = "FIGI_COMPOSITE"
    FIGI_SHARE_CLASS = "FIGI_SHARE_CLASS"
    COMMON_CODE = "COMMON_CODE"
    CINS = "CINS"
    INSTRUMENT_NAME_SUFFIX = "INSTRUMENT_NAME_SUFFIX"
    INSTRUMENT_NAME_PREFIX = "INSTRUMENT_NAME_PREFIX"
    INSTRUMENT_SHORT_NAME = "INSTRUMENT_SHORT_NAME"
    INSTRUMENT_PRODUCT_NAME = "INSTRUMENT_PRODUCT_NAME"
    ISSUER_LONG_NAME = "ISSUER_LONG_NAME"
    TICKER = "TICKER"
    LISTING_SYMBOL = "LISTING_SYMBOL"
    SIX_SYMBOL = "SIX_SYMBOL"
    OTHER = "OTHER"


class FreeTextInstrumentSearchIssuer(BaseAPIModel):
    short_name: str | None = Field(default=None, description="Legal entity short name.")
    long_name: str | None = Field(default=None, description="Legal entity long name.")
    lei: str | None = Field(
        default=None,
        description="The Legal Entity Identifier (LEI) is a 20-digit alphanumeric code to identify a legal entity. The structure is defined in ISO 17442.",
    )
    gk: int = Field(
        ...,
        description="The SIX Financial Information identifier (GK) of the legal entity.",
    )


class FreeTextInstrumentSearchMostLiquidMarket(BaseAPIModel):
    short_name: str = Field(..., description="Market short name.")
    long_name: str = Field(..., description="Market long name.")
    bc: int = Field(
        ...,
        description="Bourse Code (BC) of the market. It represents the SIX Financial Information identifier for exchanges, trading platforms, regulated or non-regulated markets and trade reporting facilities as sources of prices and related information.",
    )
    mic: str | None = Field(
        default=None,
        description="Market Identifier Code (MIC) of the market. It is based on ISO 10383 alphanumeric-4 code and represents a universal method of identifying exchanges, trading platforms, regulated or non-regulated markets and trade reporting facilities as sources of prices and related information.",
    )


class FreeTextInstrumentSearchUltimateUnderlyingInstrument(BaseAPIModel):
    short_name: str = Field(..., description="Instrument short name.")
    valor: int = Field(
        ...,
        description="Official national instrument identifier assigned by the National Numbering Agency responsible for Switzerland: SIX Financial Information.",
    )
    isin: str | None = Field(
        default=None,
        description="The International Securities Identification Number (ISIN) is a universally recognized and standardized code that uniquely identifies a financial instrument. The structure is defined in ISO 6166.",
    )


class FreeTextInstrumentSearchUnderlyingInstrument(
    FreeTextInstrumentSearchUltimateUnderlyingInstrument
):
    pass


class FreeTextInstrumentSearchHit(BaseAPIModel):
    instrument_short_name: str = Field(..., description="Instrument short name.")
    instrument_name_prefix: str = Field(
        ..., description="Prefix Instrument classification in textual form."
    )
    instrument_name_suffix: str | None = Field(
        default=None,
        description="Additional instrument type classifications in textual form.",
    )
    instrument_product_name: str | None = Field(
        default=None,
        description="A free-form descriptive name of the instrument, assigned by the issuer. E.g. 6 % Reversy on XYZ Ltd.",
    )
    valor: int = Field(
        ...,
        description="Official national instrument identifier assigned by the National Numbering Agency responsible for Switzerland: SIX Financial Information.",
    )
    isin: str | None = Field(
        default=None,
        description="The International Securities Identification Number (ISIN) is a universally recognized and standardized code that uniquely identifies a financial instrument.  Its structure is defined in ISO 6166.",
    )
    instrument_type: InstrumentType = Field(
        ...,
        description="Instrument classification allocated by SIX Financial Information. The Instrument Type embodies a more granular categorization compared to the Security Type.",
    )
    security_type: SecurityType = Field(
        ...,
        description="Security classification allocated by SIX Financial Information.  The Security Type embodies a broader categoriatzion compared to the Instrument Type, specifially tailored for optimal presentation in display applications.",
    )
    instrument_status: InstrumentStatus = Field(
        ...,
        description='Status indicating whether an instrument is active or not. Provided that the instrument is still active, this may include further information such as "in default" or "In liquidation/dissolution".',
    )
    language: Language | None = Field(
        default=None,
        description="Main language applicable to the financial instrument according to ISO 639 alpha-2 code. It can be different from the issuing company's main language.",
    )
    issuer: FreeTextInstrumentSearchIssuer | None = None
    most_liquid_market: FreeTextInstrumentSearchMostLiquidMarket | None = None
    nominal_amount: float | None = Field(
        default=None,
        description="Nominal amount or par value of an instrument (e.g. 100 for a share with a nominal value of CHF 100). For debt instruments, only the currency but no nominal value is issued.",
    )
    nominal_currency: str | None = Field(
        default=None,
        description="Nominal currency, as specified by SIX, typically follows the ISO 4217 alpha-3 code. For cryptocurrencies, the Cryptocurrency Symbol in Instrument Symbology can be used for reference.",
    )
    nominal_paid_up: float | None = Field(
        default=None,
        description="If the instrument is partly paid-up as opposed to fully paid-up, the currently paid-in amount is recorded here. No entry is made for fully paid-up instruments.",
    )
    instrument_unit_type: InstrumentUnitType | None = Field(
        default=None,
        description="Indicates the unit of measurement in which the instrument quantity is expressed: Per instrument or per nominal. For prices, this is the unit in which the instrument is traded.",
    )
    instrument_unit_size: float | None = Field(
        default=None,
        description='It indicates the smallest denominations. Break-down of debt instrument by their nominal values (in Switzerland usually CHF 1000 and CHF 5000). For trusts the decimal places are indicated here, e.g. ",001" for proportions with fractions of 3 decimal places.',
    )
    current_coupon_rate: float | None = Field(
        default=None, description="Current interest rate."
    )
    current_coupon_type: CurrentCouponType | None = Field(
        default=None,
        description="Represents the characteristics of an interest payment made for an instrument. Interest payments are regular payments, their amounts are either fixed or depend on certain reference sizes such as reference interest rates.",
    )
    maturity_date: date | None = Field(
        default=None,
        description="Latest possible redemption date provided in the prospectus according to ISO 8601. This applies to all instruments for which only one maturity date was stated. If several dates were provided for the financial instrument (e.g. for ABS / Asset-Backed Securities), i.e. an expected maturity and a legal maturity, then this field will contain the date of the earliest possible maturity (Expected Maturity).",
    )
    maturity_type: MaturityType | None = Field(
        default=None,
        description="Indicates whether an instrument has a fixed final expiry date or none at all",
    )
    base_currency: str | None = Field(
        default=None,
        description="Base currency, as specified by SIX, typically follows the ISO 4217 alpha-3 code. For cryptocurrencies, the Cryptocurrency Symbol in Instrument Symbology can be used for reference.",
    )
    trading_currency: str | None = Field(
        default=None,
        description="Trading currency, as specified by SIX, typically follows the ISO 4217 alpha-3 code. For cryptocurrencies, the Cryptocurrency Symbol in Instrument Symbology can be used for reference.",
    )
    base_crypto_symbol: str | None = Field(
        default=None,
        description="Base cryptocurrency symbol used in currency dealings.",
    )
    trading_crypto_symbol: str | None = Field(
        default=None,
        description="Trading cryptocurrency symbol used in currency dealings.",
    )
    contract_type: ContractType | None = Field(
        default=None,
        description="Indicates the type of underlying to which the exchange-traded derivatives relates (e.g. ETD on interest, etc.).",
    )
    contract_symbol: str | None = Field(
        default=None,
        description="Identification used by the exchange to identify the specification of a contract. In some markets also known as Product Code.",
    )
    underlying_instrument: FreeTextInstrumentSearchUnderlyingInstrument | None = None
    ultimate_underlying_instrument: (
        FreeTextInstrumentSearchUltimateUnderlyingInstrument | None
    ) = None
    option_type: OptionType | None = Field(
        default=None,
        description="Defines the type of the option from an investor's point of view. E.g. right to purchase (call), right to sell (put).",
    )
    option_strike_price: float | None = Field(
        default=None,
        description='Price at which the holder of a call option can buy the underlying securities or the holder of a put option can sell. Also referred to as exercise price. Depending on the product type, strike prices define whether an embedded option in the product is "in the money" or not.',
    )
    option_strike_price_currency: str | None = Field(
        default=None,
        description="Strike Price Currency, as specified by SIX, typically follows the ISO 4217 alpha-3 code. For cryptocurrencies, the Cryptocurrency Symbol in Instrument Symbology can be used for reference.",
    )
    exercise_type: ExerciseType | None = Field(
        default=None,
        description='American style: Can be exercised at any time for the whole period - the data "exercise from" and "exercise until" are thus different. European style: Exercise at maturity or expiry. In this case the data "exercise from" and "exercise until" are identical. Bermuda style: Exercise on pre-defined days within an entire period of exercise.',
    )
    expiration_date: date | None = Field(
        default=None,
        description="The date by which an option contract is abandoned and becomes worthless unless it is exercised.",
    )
    contract_size: float | None = Field(
        default=None,
        description="Indicates the quantity of underlying instruments or the notional amount of the contract. At issuance, for ETDs on equity this amount is identical with the Contract Multiplier. After an adjustment, the Contract Size can change and may be different to the Contract Multiplier.",
    )
    contract_unit_type: ContractUnitType | None = Field(
        default=None,
        description="Type of quantity the Contract Size and Contract Multiplier refer to.",
    )
    contract_multiplier: float | None = Field(
        default=None,
        description="The multiplier is the stated quantity or value to calculate the total contract value based on the quoted price.",
    )
    six_version_number: int | None = Field(
        default=None,
        description="SIX Financial Information assigns this version number to a contract. After changes in capital or other corporate actions a new version of an option or a future can be created and the version number is increased accordingly.",
    )


class FreeTextInstrumentSearchHighlightsItem(BaseAPIModel):
    matching_description: InstrumentMatchingDescription = Field(
        ...,
        description="A human-readable explanation detailing the alignment between the search term and the content of a particular result.",
    )


class FreeTextInstrumentSearchInstrumentsItem(BaseAPIModel):
    hit: FreeTextInstrumentSearchHit | None = None
    normalized_score: float = Field(
        ...,
        description="A numerical value ranging from 0 to 1, representing the degree of correlation between the search term and a given result. A perfect match results in a score of 1, offering a standardized measure of relevance.",
    )
    highlights: list[FreeTextInstrumentSearchHighlightsItem] = Field(
        ...,
        description="A list of descriptions outlining the reasons why a particular search term led to a corresponding match. These highlights provide insights into the contextual relevance of the result.",
    )


class FreeTextInstrumentSearchInstruments(BaseAPIModel):
    instruments: list[FreeTextInstrumentSearchInstrumentsItem] = Field(
        ...,
        description="Search instruments by free-text names, by identifiers, by listing symbol and by trading symbols.",
    )


class FreeTextInstrumentSearch(BaseAPIModel):
    free_text_search: FreeTextInstrumentSearchInstruments | None = None


class FreeTextInstrumentSearchData(BaseAPIModel):
    search: FreeTextInstrumentSearch | None = None


class FreeTextInstrumentsSearchResponsePayload(BaseResponsePayload):
    data: FreeTextInstrumentSearchData | None = None
