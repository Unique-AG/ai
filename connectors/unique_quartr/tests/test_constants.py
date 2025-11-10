from unique_quartr.constants.document_types import DocumentType
from unique_quartr.constants.event_types import (
    EVENT_TYPE_MAPPING,
    EventSubType,
    EventType,
)


class TestDocumentType:
    """Test cases for DocumentType enum."""

    def test_document_type_values(self):
        """Test DocumentType enum values are correct."""
        assert DocumentType.SLIDES == 5
        assert DocumentType.REPORT == 6
        assert DocumentType.QUARTERLY_REPORT_10Q == 7
        assert DocumentType.EARNINGS_RELEASE_8K == 10
        assert DocumentType.ANNUAL_REPORT_10K == 11
        assert DocumentType.ANNUAL_REPORT == 12
        assert DocumentType.ANNUAL_REPORT_20F == 13
        assert DocumentType.EARNINGS_RELEASE_6K == 14
        assert DocumentType.TRANSCRIPT == 15
        assert DocumentType.INTERIM_REPORT == 17
        assert DocumentType.ANNUAL_REPORT_40F == 18
        assert DocumentType.PRESS_RELEASE == 19
        assert DocumentType.EARNINGS_RELEASE == 20
        assert DocumentType.IN_HOUSE_TRANSCRIPT == 22

    def test_document_type_form_property(self):
        """Test DocumentType.form property returns correct values."""
        assert DocumentType.QUARTERLY_REPORT_10Q.form == "10-Q"
        assert DocumentType.EARNINGS_RELEASE_8K.form == "8-K"
        assert DocumentType.ANNUAL_REPORT_10K.form == "10-K"
        assert DocumentType.ANNUAL_REPORT_20F.form == "20-F"
        assert DocumentType.EARNINGS_RELEASE_6K.form == "6-K"
        assert DocumentType.ANNUAL_REPORT_40F.form == "40-F"
        assert DocumentType.IN_HOUSE_TRANSCRIPT.form == "In-house transcript"

    def test_document_type_form_property_none(self):
        """Test DocumentType.form property returns None for documents without forms."""
        assert DocumentType.SLIDES.form is None
        assert DocumentType.REPORT.form is None
        assert DocumentType.TRANSCRIPT.form is None
        assert DocumentType.PRESS_RELEASE.form is None

    def test_document_type_name_property(self):
        """Test DocumentType.name property returns correct values."""
        assert DocumentType.SLIDES.name == "Slides"
        assert DocumentType.REPORT.name == "Report"
        assert DocumentType.QUARTERLY_REPORT_10Q.name == "Quarterly report"
        assert DocumentType.EARNINGS_RELEASE_8K.name == "Earnings release"
        assert DocumentType.ANNUAL_REPORT_10K.name == "Annual report"
        assert DocumentType.TRANSCRIPT.name == "Transcript"
        assert DocumentType.INTERIM_REPORT.name == "Interim report"
        assert DocumentType.PRESS_RELEASE.name == "Press release"
        assert DocumentType.IN_HOUSE_TRANSCRIPT.name == "In-house transcript"

    def test_document_type_emoji_property(self):
        """Test DocumentType.emoji property returns correct emojis."""
        assert DocumentType.TRANSCRIPT.emoji == "🗒️"
        assert DocumentType.SLIDES.emoji == "📊"
        assert DocumentType.REPORT.emoji == "📄"
        assert DocumentType.QUARTERLY_REPORT_10Q.emoji == "📑"
        assert DocumentType.EARNINGS_RELEASE_8K.emoji == "📢"
        assert DocumentType.ANNUAL_REPORT_10K.emoji == "📘"
        assert DocumentType.PRESS_RELEASE.emoji == "🗞️"
        assert DocumentType.EARNINGS_RELEASE.emoji == "💰"
        assert DocumentType.IN_HOUSE_TRANSCRIPT.emoji == "🎤"

    def test_document_type_get_file_prefix_with_form(self):
        """Test get_file_prefix with documents that have forms."""
        assert (
            DocumentType.QUARTERLY_REPORT_10Q.get_file_prefix()
            == "Quarterly report (10-Q)"
        )
        assert (
            DocumentType.ANNUAL_REPORT_10K.get_file_prefix() == "Annual report (10-K)"
        )
        assert (
            DocumentType.EARNINGS_RELEASE_8K.get_file_prefix()
            == "Earnings release (8-K)"
        )

    def test_document_type_get_file_prefix_without_form(self):
        """Test get_file_prefix with documents without forms."""
        assert DocumentType.SLIDES.get_file_prefix() == "Slides"
        assert DocumentType.REPORT.get_file_prefix() == "Report"
        assert DocumentType.TRANSCRIPT.get_file_prefix() == "Transcript"


class TestEventType:
    """Test cases for EventType enum."""

    def test_event_type_values(self):
        """Test EventType enum values are correct."""
        assert EventType.ANALYST_DAY == "Analyst Day"
        assert EventType.ANNUAL_GENERAL_MEETING == "Annual General Meeting"
        assert EventType.BUSINESS_COMBINATION == "Business Combination"
        assert EventType.C_LEVEL_SITDOWN == "C-level Sitdown"
        assert EventType.CAPITAL_MARKETS_DAY == "Capital Markets Day"
        assert EventType.CAPITAL_RAISE == "Capital Raise"
        assert EventType.CONFERENCE == "Conference"
        assert EventType.EARNINGS_CALL == "Earnings Call"
        assert (
            EventType.EXTRAORDINARY_GENERAL_MEETING == "Extraordinary General Meeting"
        )
        assert EventType.FDA_ANNOUNCEMENT == "FDA Announcement"
        assert EventType.FIRESIDE_CHAT == "Fireside Chat"
        assert EventType.INVESTOR_DAY == "Investor Day"
        assert EventType.M_AND_A_ANNOUNCEMENT == "M&A Announcement"
        assert EventType.OUTLOOK_GUIDANCE_UPDATE == "Outlook / Guidance Update"
        assert EventType.PARTNERSHIPS_COLLABORATIONS == "Partnerships / Collaborations"
        assert EventType.PRODUCT_SERVICE_LAUNCH == "Product / Service Launch"
        assert EventType.SLIDES == "Slides"
        assert EventType.TRADING_UPDATE == "Trading Update"
        assert EventType.UPDATE_BRIEFING == "Update / Briefing"


class TestEventSubType:
    """Test cases for EventSubType enum."""

    def test_event_subtype_values(self):
        """Test EventSubType enum values are correct."""
        assert EventSubType.ANALYST_DAY == 33
        assert EventSubType.AGM == 4
        assert EventSubType.SCHEME_MEETING == 284
        assert EventSubType.BUSINESS_COMBINATION == 32
        assert EventSubType.C_LEVEL_SITDOWN == 13
        assert EventSubType.CEO_SITDOWN == 14
        assert EventSubType.CMD == 2
        assert EventSubType.CAPITAL_RAISE == 18
        assert EventSubType.CONFERENCE == 237
        assert EventSubType.Q1 == 26
        assert EventSubType.Q2 == 27
        assert EventSubType.Q3 == 28
        assert EventSubType.Q4 == 29
        assert EventSubType.H1 == 35
        assert EventSubType.H2 == 36
        assert EventSubType.EGM == 6
        assert EventSubType.FDA_ANNOUNCEMENT == 19
        assert EventSubType.FIRESIDE_CHAT == 12
        assert EventSubType.INVESTOR_DAY == 31
        assert EventSubType.M_AND_A_ANNOUNCEMENT == 17
        assert EventSubType.GUIDANCE == 8
        assert EventSubType.PARTNERSHIP == 10
        assert EventSubType.COLLABORATION == 11
        assert EventSubType.PRODUCT_LAUNCH == 23
        assert EventSubType.SERVICE_LAUNCH == 24
        assert EventSubType.INVESTOR_PRESENTATION == 275
        assert EventSubType.CORPORATE_PRESENTATION == 279
        assert EventSubType.COMPANY_PRESENTATION == 283
        assert EventSubType.TRADING_UPDATE == 202
        assert EventSubType.STATUS_UPDATE == 21
        assert EventSubType.INVESTOR_UPDATE == 239
        assert EventSubType.ESG_UPDATE == 240
        assert EventSubType.STUDY_UPDATE == 280
        assert EventSubType.STUDY_RESULT == 281
        assert EventSubType.KOL_EVENT == 285


class TestEventTypeMapping:
    """Test cases for EVENT_TYPE_MAPPING."""

    def test_event_type_mapping_completeness(self):
        """Test that all EventTypes have mappings."""
        for event_type in EventType:
            assert event_type in EVENT_TYPE_MAPPING, f"{event_type} not in mapping"

    def test_earnings_call_mapping(self):
        """Test earnings call event type mapping."""
        mapping = EVENT_TYPE_MAPPING[EventType.EARNINGS_CALL]
        assert EventSubType.Q1 in mapping
        assert EventSubType.Q2 in mapping
        assert EventSubType.Q3 in mapping
        assert EventSubType.Q4 in mapping
        assert EventSubType.H1 in mapping
        assert EventSubType.H2 in mapping
        assert len(mapping) == 6

    def test_annual_general_meeting_mapping(self):
        """Test AGM event type mapping."""
        mapping = EVENT_TYPE_MAPPING[EventType.ANNUAL_GENERAL_MEETING]
        assert EventSubType.AGM in mapping
        assert EventSubType.SCHEME_MEETING in mapping
        assert len(mapping) == 2

    def test_c_level_sitdown_mapping(self):
        """Test C-level sitdown event type mapping."""
        mapping = EVENT_TYPE_MAPPING[EventType.C_LEVEL_SITDOWN]
        assert EventSubType.C_LEVEL_SITDOWN in mapping
        assert EventSubType.CEO_SITDOWN in mapping
        assert len(mapping) == 2

    def test_partnerships_collaborations_mapping(self):
        """Test partnerships/collaborations event type mapping."""
        mapping = EVENT_TYPE_MAPPING[EventType.PARTNERSHIPS_COLLABORATIONS]
        assert EventSubType.PARTNERSHIP in mapping
        assert EventSubType.COLLABORATION in mapping
        assert len(mapping) == 2

    def test_product_service_launch_mapping(self):
        """Test product/service launch event type mapping."""
        mapping = EVENT_TYPE_MAPPING[EventType.PRODUCT_SERVICE_LAUNCH]
        assert EventSubType.PRODUCT_LAUNCH in mapping
        assert EventSubType.SERVICE_LAUNCH in mapping
        assert len(mapping) == 2

    def test_slides_mapping(self):
        """Test slides event type mapping."""
        mapping = EVENT_TYPE_MAPPING[EventType.SLIDES]
        assert EventSubType.INVESTOR_PRESENTATION in mapping
        assert EventSubType.CORPORATE_PRESENTATION in mapping
        assert EventSubType.COMPANY_PRESENTATION in mapping
        assert len(mapping) == 3

    def test_update_briefing_mapping(self):
        """Test update/briefing event type mapping."""
        mapping = EVENT_TYPE_MAPPING[EventType.UPDATE_BRIEFING]
        assert EventSubType.STATUS_UPDATE in mapping
        assert EventSubType.INVESTOR_UPDATE in mapping
        assert EventSubType.ESG_UPDATE in mapping
        assert EventSubType.STUDY_UPDATE in mapping
        assert EventSubType.STUDY_RESULT in mapping
        assert EventSubType.KOL_EVENT in mapping
        assert len(mapping) == 6

    def test_single_subtype_mappings(self):
        """Test event types that map to a single subtype."""
        single_mappings = {
            EventType.ANALYST_DAY: EventSubType.ANALYST_DAY,
            EventType.BUSINESS_COMBINATION: EventSubType.BUSINESS_COMBINATION,
            EventType.CAPITAL_MARKETS_DAY: EventSubType.CMD,
            EventType.CAPITAL_RAISE: EventSubType.CAPITAL_RAISE,
            EventType.CONFERENCE: EventSubType.CONFERENCE,
            EventType.EXTRAORDINARY_GENERAL_MEETING: EventSubType.EGM,
            EventType.FDA_ANNOUNCEMENT: EventSubType.FDA_ANNOUNCEMENT,
            EventType.FIRESIDE_CHAT: EventSubType.FIRESIDE_CHAT,
            EventType.INVESTOR_DAY: EventSubType.INVESTOR_DAY,
            EventType.M_AND_A_ANNOUNCEMENT: EventSubType.M_AND_A_ANNOUNCEMENT,
            EventType.OUTLOOK_GUIDANCE_UPDATE: EventSubType.GUIDANCE,
            EventType.TRADING_UPDATE: EventSubType.TRADING_UPDATE,
        }

        for event_type, expected_subtype in single_mappings.items():
            mapping = EVENT_TYPE_MAPPING[event_type]
            assert len(mapping) == 1
            assert mapping[0] == expected_subtype
