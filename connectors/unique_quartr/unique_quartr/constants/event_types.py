from enum import IntEnum, StrEnum


class EventType(StrEnum):
    ANALYST_DAY = "Analyst Day"
    ANNUAL_GENERAL_MEETING = "Annual General Meeting"
    BUSINESS_COMBINATION = "Business Combination"
    C_LEVEL_SITDOWN = "C-level Sitdown"
    CAPITAL_MARKETS_DAY = "Capital Markets Day"
    CAPITAL_RAISE = "Capital Raise"
    CONFERENCE = "Conference"
    EARNINGS_CALL = "Earnings Call"
    EXTRAORDINARY_GENERAL_MEETING = "Extraordinary General Meeting"
    FDA_ANNOUNCEMENT = "FDA Announcement"
    FIRESIDE_CHAT = "Fireside Chat"
    INVESTOR_DAY = "Investor Day"
    M_AND_A_ANNOUNCEMENT = "M&A Announcement"
    OUTLOOK_GUIDANCE_UPDATE = "Outlook / Guidance Update"
    PARTNERSHIPS_COLLABORATIONS = "Partnerships / Collaborations"
    PRODUCT_SERVICE_LAUNCH = "Product / Service Launch"
    SLIDES = "Slides"
    TRADING_UPDATE = "Trading Update"
    UPDATE_BRIEFING = "Update / Briefing"


class EventSubType(IntEnum):
    # Analyst Day
    ANALYST_DAY = 33

    # Annual General Meeting
    AGM = 4
    SCHEME_MEETING = 284

    # Business Combination
    BUSINESS_COMBINATION = 32

    # C-level Sitdown
    C_LEVEL_SITDOWN = 13
    CEO_SITDOWN = 14

    # Capital Markets Day
    CMD = 2

    # Capital Raise
    CAPITAL_RAISE = 18

    # Conference
    CONFERENCE = 237

    # Earnings Call
    Q1 = 26
    Q2 = 27
    Q3 = 28
    Q4 = 29
    H1 = 35
    H2 = 36

    # Extraordinary General Meeting
    EGM = 6

    # FDA Announcement
    FDA_ANNOUNCEMENT = 19

    # Fireside Chat
    FIRESIDE_CHAT = 12

    # Investor Day
    INVESTOR_DAY = 31

    # M&A Announcement
    M_AND_A_ANNOUNCEMENT = 17

    # Outlook / Guidance Update
    GUIDANCE = 8

    # Partnerships / Collaborations
    PARTNERSHIP = 10
    COLLABORATION = 11

    # Product / Service Launch
    PRODUCT_LAUNCH = 23
    SERVICE_LAUNCH = 24

    # Slides
    INVESTOR_PRESENTATION = 275
    CORPORATE_PRESENTATION = 279
    COMPANY_PRESENTATION = 283

    # Trading Update
    TRADING_UPDATE = 202

    # Update / Briefing
    STATUS_UPDATE = 21
    INVESTOR_UPDATE = 239
    ESG_UPDATE = 240
    STUDY_UPDATE = 280
    STUDY_RESULT = 281
    KOL_EVENT = 285


EVENT_TYPE_MAPPING = {
    EventType.ANALYST_DAY: [EventSubType.ANALYST_DAY],
    EventType.ANNUAL_GENERAL_MEETING: [
        EventSubType.AGM,
        EventSubType.SCHEME_MEETING,
    ],
    EventType.BUSINESS_COMBINATION: [EventSubType.BUSINESS_COMBINATION],
    EventType.C_LEVEL_SITDOWN: [
        EventSubType.C_LEVEL_SITDOWN,
        EventSubType.CEO_SITDOWN,
    ],
    EventType.CAPITAL_MARKETS_DAY: [EventSubType.CMD],
    EventType.CAPITAL_RAISE: [EventSubType.CAPITAL_RAISE],
    EventType.CONFERENCE: [EventSubType.CONFERENCE],
    EventType.EARNINGS_CALL: [
        EventSubType.Q1,
        EventSubType.Q2,
        EventSubType.Q3,
        EventSubType.Q4,
        EventSubType.H1,
        EventSubType.H2,
    ],
    EventType.EXTRAORDINARY_GENERAL_MEETING: [EventSubType.EGM],
    EventType.FDA_ANNOUNCEMENT: [EventSubType.FDA_ANNOUNCEMENT],
    EventType.FIRESIDE_CHAT: [EventSubType.FIRESIDE_CHAT],
    EventType.INVESTOR_DAY: [EventSubType.INVESTOR_DAY],
    EventType.M_AND_A_ANNOUNCEMENT: [EventSubType.M_AND_A_ANNOUNCEMENT],
    EventType.OUTLOOK_GUIDANCE_UPDATE: [EventSubType.GUIDANCE],
    EventType.PARTNERSHIPS_COLLABORATIONS: [
        EventSubType.PARTNERSHIP,
        EventSubType.COLLABORATION,
    ],
    EventType.PRODUCT_SERVICE_LAUNCH: [
        EventSubType.PRODUCT_LAUNCH,
        EventSubType.SERVICE_LAUNCH,
    ],
    EventType.SLIDES: [
        EventSubType.INVESTOR_PRESENTATION,
        EventSubType.CORPORATE_PRESENTATION,
        EventSubType.COMPANY_PRESENTATION,
    ],
    EventType.TRADING_UPDATE: [EventSubType.TRADING_UPDATE],
    EventType.UPDATE_BRIEFING: [
        EventSubType.STATUS_UPDATE,
        EventSubType.INVESTOR_UPDATE,
        EventSubType.ESG_UPDATE,
        EventSubType.STUDY_UPDATE,
        EventSubType.STUDY_RESULT,
        EventSubType.KOL_EVENT,
    ],
}
