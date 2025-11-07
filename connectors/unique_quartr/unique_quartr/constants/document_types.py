from enum import IntEnum


class DocumentType(IntEnum):
    SLIDES = 5
    REPORT = 6
    QUARTERLY_REPORT_10Q = 7
    EARNINGS_RELEASE_8K = 10
    ANNUAL_REPORT_10K = 11
    ANNUAL_REPORT = 12
    ANNUAL_REPORT_20F = 13
    EARNINGS_RELEASE_6K = 14
    TRANSCRIPT = 15
    INTERIM_REPORT = 17
    ANNUAL_REPORT_40F = 18
    PRESS_RELEASE = 19
    EARNINGS_RELEASE = 20
    IN_HOUSE_TRANSCRIPT = 22

    @property
    def form(self) -> str | None:
        forms = {
            self.QUARTERLY_REPORT_10Q: "10-Q",
            self.EARNINGS_RELEASE_8K: "8-K",
            self.ANNUAL_REPORT_10K: "10-K",
            self.ANNUAL_REPORT_20F: "20-F",
            self.EARNINGS_RELEASE_6K: "6-K",
            self.ANNUAL_REPORT_40F: "40-F",
            self.IN_HOUSE_TRANSCRIPT: "In-house transcript",
        }
        return forms.get(self)

    @property
    def name(self) -> str:
        names = {
            self.SLIDES: "Slides",
            self.REPORT: "Report",
            self.QUARTERLY_REPORT_10Q: "Quarterly report",
            self.EARNINGS_RELEASE_8K: "Earnings release",
            self.ANNUAL_REPORT_10K: "Annual report",
            self.ANNUAL_REPORT: "Annual report",
            self.ANNUAL_REPORT_20F: "Annual report",
            self.EARNINGS_RELEASE_6K: "Earnings release",
            self.TRANSCRIPT: "Transcript",
            self.INTERIM_REPORT: "Interim report",
            self.ANNUAL_REPORT_40F: "Annual report",
            self.PRESS_RELEASE: "Press release",
            self.EARNINGS_RELEASE: "Earnings release",
            self.IN_HOUSE_TRANSCRIPT: "In-house transcript",
        }
        return names[self]

    @property
    def emoji(self) -> str:
        emojis = {
            self.TRANSCRIPT: "🗒️",
            self.SLIDES: "📊",
            self.REPORT: "📄",
            self.QUARTERLY_REPORT_10Q: "📑",
            self.EARNINGS_RELEASE_8K: "📢",
            self.ANNUAL_REPORT_10K: "📘",
            self.ANNUAL_REPORT_20F: "📙",
            self.EARNINGS_RELEASE_6K: "📣",
            self.INTERIM_REPORT: "📜",
            self.ANNUAL_REPORT_40F: "📕",
            self.PRESS_RELEASE: "🗞️",
            self.EARNINGS_RELEASE: "💰",
            self.IN_HOUSE_TRANSCRIPT: "🎤",
        }
        return emojis[self]

    def get_file_prefix(self) -> str:
        if self.form:
            return f"{self.name} ({self.form})"
        return self.name
