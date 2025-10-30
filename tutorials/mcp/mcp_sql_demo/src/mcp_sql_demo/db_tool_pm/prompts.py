DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = (
    "You can use the PM_Positions Tool also known as the pm book for searching positions pf a pm book about stock and other instruments and how exposed they are."
    "always use this tool if you are asked about exposure or position sizes. The pm book contains information about stocks and instruments held in portfolios along with their exposure and position sizes."
    'if asked about "what are the equities with the biggest exposure" then use this tool and just let it return all the data'
)

DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT = (
    "the data is presented to you in the form [(9, 'Rates', 'IEF', '7–10Y U.S. Treasuries', 'Long', Decimal('0.120000'), Decimal('240.00'), 'alice@alphabet.example')]\n\n"
    "Do not include the email address in the output and also do not include the id in the beginning this number is no use. (in the example above its the 2 in front that does not add value.)\n\n"
    "always make that a table when you present the data to the user.\n\n"
    "it must be in markdown format.\n\n"
    "anything you say around it must embed the table.\n\n"
    "Format the data you receive always as a table showing all the instrument data information you have found.\n\n"
)

DEFAULT_TOOL_DESCRIPTION = "Search a database of stocks, or instruments for relevant information on price, sector and stock ticker "
