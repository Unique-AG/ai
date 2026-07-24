"""Generate the bundled sample Excel workbook used to seed SQLite."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

# tutorials/mcp/mcp_sqlite_excel/data
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_DEFAULT_OUTPUT = _DATA_DIR / "sample_portfolio.xlsx"

POSITIONS = [
    ("Rates", "IEF", "7–10Y U.S. Treasuries", "Long", 0.12, 240, "alice@alphabet.example"),
    ("Equity Long", "MSFT", "Microsoft Corp", "Long", 0.08, 160, "alice@alphabet.example"),
    ("Equity Long", "AAPL", "Apple Inc", "Long", 0.06, 120, "alice@alphabet.example"),
    ("Equity Long", "JNJ", "Johnson & Johnson", "Long", 0.04, 80, "bob@alphabet.example"),
    ("Alternatives", "GLD", "SPDR Gold Shares", "Long", 0.05, 100, "bob@alphabet.example"),
    ("Equity Long", "TSLA", "Tesla Inc", "Short", 0.03, -60, "alice@alphabet.example"),
    ("Rates", "TLT", "20+Y U.S. Treasuries", "Long", 0.07, 140, "carol@alphabet.example"),
    ("Equity Long", "SPY", "S&P 500 ETF", "Long", 0.10, 200, "carol@alphabet.example"),
]

INSTRUMENTS = [
    ("IEF", "ETF", "Fixed Income", "USD"),
    ("MSFT", "Equity", "Technology", "USD"),
    ("AAPL", "Equity", "Technology", "USD"),
    ("JNJ", "Equity", "Healthcare", "USD"),
    ("GLD", "ETF", "Commodities", "USD"),
    ("TSLA", "Equity", "Consumer Discretionary", "USD"),
    ("TLT", "ETF", "Fixed Income", "USD"),
    ("SPY", "ETF", "Broad Market", "USD"),
]


def generate(output_path: Path | None = None) -> Path:
    """Write sample_portfolio.xlsx with positions + instruments sheets."""
    output = output_path or _DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()

    positions = wb.active
    positions.title = "positions"
    positions.append(["Sleeve", "Ticker", "Instrument", "Direction", "Target Weight", "Position MM", "Email"])
    for row in POSITIONS:
        positions.append(list(row))

    instruments = wb.create_sheet("instruments")
    instruments.append(["Ticker", "Asset Class", "Sector", "Currency"])
    for row in INSTRUMENTS:
        instruments.append(list(row))

    wb.save(output)
    return output


def main() -> None:
    path = generate()
    print(f"Wrote sample workbook to {path}")


if __name__ == "__main__":
    main()
