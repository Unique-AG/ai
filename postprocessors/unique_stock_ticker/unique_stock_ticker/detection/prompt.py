SYSTEM_MESSAGE_STOCK_TICKER_QUERY = """
Below are a message from a user and a message from the assistant.
If a company or ETF (Exchange Traded Fund) is mentioned in the messages, you should load their stock symbols and output them in a specific format.


IMPORTANT:
Only output tickers if the company stock (or ETF) is mentioned in the user message or assistant message, not for e.g its bonds.

Example:
User Message:
'''I want to invest in Apple'''
Assistant Message:
'''I recommend you to buy Apple's stock'''
Response:
{"tickers": [{"explanation": "AAPL is the only ticker for Apple", "ticker": "AAPL", "company_name": "Apple", "instrument_type": "equity"}]}
Example:
User Message:
'''I want to invest in Oklo'''
Assistant Message:
'''Oklo is a risky investment according to our internal risk assessment'''
Response:
{"tickers": [{"explanation": "OKLO is the only ticker for Oklo", "ticker": "OKLO", "company_name": "Oklo", "instrument_type": "equity"}]}
Example:
User Message:
'''What about the VanEck Uranium and Nuclear ETF?'''
Assistant Message:
'''Our internal rating for this ETF is Buy'''
Response:
{"tickers": [{"explanation": "NLR is the only ticker for the VanEck Uranium and Nuclear ETF", "ticker": "NLR", "company_name": "VanEck Uranium and Nuclear ETF", "instrument_type": "etf"}]}
""".strip()

USER_MESSAGE_STOCK_TICKER_QUERY = """Identify the stock symbols in the user message and assistant message and return them in the format specified in the system message.
User Message:
'''${user_message}'''
Assistant Message:
'''${assistant_message}'''
Response:"""
