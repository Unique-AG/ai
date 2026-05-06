DEFAULT_SCHEMA = {
    "author_institution": {
        "type": "string",
        "description": "Name of the institution (for example, investment bank or broker) that issued the research report.",
    },
    "analyst_name": {
        "type": "string",
        "description": "Name of the analyst person who wrote the research report",
    },
    "publication_date": {
        "type": "string",
        "description": "Date of the research report publication in %Y-%m-%d format. Must be a specific date, not a range of dates: if only a year, quarter or month is mentioned, then must be the last date of that period. For example: if only '2023' is mentioned, then return the last date of the year 2023 such as '2023-12-31' if only 'Q2 2023' is mentioned, then return the last date of Quarter 2 of 2023 such as '2023-06-30' if only 'September 2023' is mentioned, then return the last date of September 2023 such as '2023-09-30' The publication date may sometimes be referred to as published date, posting date, report date, etc. in the text; or it may not be labeled at all.",
    },
    "text_summary": {
        "type": "string",
        "description": 'Brief summary of the research report, focusing on factual statements and quantitative metrics. Include only summary of facts mentioned in the report, don\'t include filler words like "the report discusses..."',
    },
    "upcoming_catalysts": {
        "type": "string",
        "description": "List of upcoming events that may be significant to a given company, according to the report. Include dates / periods and specific metrics where possible. Examples:     WidgetMax X123 expected to be released at the WidgetCon event on August 1 2023, where the SuperCool AI feature is expected to be demoed.     Expecting guidance from the next earnings report on May 6 2028 to clarify the path forward for EMEA expansion.     Congress decision on the Widget funding bill is expected in Q1 2027. Passage of the bill should be a tailwind for the company.",
    },
}
