"""Tool descriptions for the trade reconciliation MCP tools."""

GET_CUSTOMER_BOOK_CASHFLOWS_DESCRIPTION = (
    "Return rows from the customer (book) cash flows table. These are the "
    "internal trades produced by our trading book (BFX trade id, instrument, "
    "ccy, account, counterparty, side, trade date, settlement date, gross "
    "amount). Use optional filters to narrow the result; all filters are "
    "ANDed together."
)

GET_COUNTERPARTY_EMAIL_CASHFLOWS_DESCRIPTION = (
    "Return rows from the counterparty (email) cash flows table. These rows "
    "are mined from counterparty emails (settlement instructions, "
    "confirmations, etc.). Each row carries a vendor, action, amount, ccy, "
    "value date and reconciliation status (MATCHED / UNMATCHED) plus the id "
    "of the customer cash flow it has been reconciled to (if any)."
)

MATCH_CASHFLOWS_DESCRIPTION = (
    "Reconcile counterparty (email) cash flows against the customer (book) "
    "cash flows. By default attempts to match every email row currently in "
    "UNMATCHED status; pass email_ids to restrict the run. The matcher uses: "
    "counterparty == vendor (case-insensitive), ccy equal, side == action, "
    "|gross_amt - amount| within tolerance, and value_date equal to either "
    "trade_date or settl_date. The returned payload includes a reason for "
    "every row so the caller can explain why something did not match."
)

SAVE_COUNTERPARTY_EMAIL_CASHFLOW_DESCRIPTION = (
    "Insert a new counterparty (email) cash flow row and immediately try to "
    "reconcile it against the customer (book) cash flows. Returns the "
    "inserted row plus the match outcome (matched customer cash flow id and "
    "amount difference, or the reason why no match was found)."
)

RESET_DEMO_DATA_DESCRIPTION = (
    "Reset the trade reconciliation demo to its baseline. This is a "
    "DESTRUCTIVE operation: it drops and recreates both cash-flow tables and "
    "re-inserts the original seed rows. All counterparty (email) cash flows go "
    "back to UNMATCHED status and any rows added during the demo are removed, "
    "so the reconciliation can be demonstrated from scratch. Use this between "
    "demo runs to get a clean, predictable starting state."
)
