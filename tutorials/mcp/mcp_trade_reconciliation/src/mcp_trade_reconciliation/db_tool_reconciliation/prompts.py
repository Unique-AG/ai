"""Tool descriptions and Unique AI prompt metadata for the trade reconciliation MCP tools.

Unique reads two keys off each MCP tool's ``_meta`` and renders them as the tool's
"System Prompt: Tool Usage Instructions" and "System Prompt: Tool Response Format
Instructions". Attach them via :func:`tool_meta` (same pattern as the rm_mcps servers).
"""

SYSTEM_PROMPT_META_KEY = "unique.app/system-prompt"
FORMAT_INFO_META_KEY = "unique.app/tool-format-information"

TOOL_PROMPTS = {
    "Get_Customer_Book_Cashflows": {
        "system_prompt": (
            "READ. Lists internal book trades. All filters optional and ANDed: `counterparty` "
            "(ILIKE, e.g. 'Goldman%'), `ccy` (ISO code), `side` (BUY / SELL / SHORT SELL / "
            "BUY TO COVER), `trade_date` / `settl_date` (YYYY-MM-DD), `instrument` (ILIKE), "
            "`limit` (default 200). Use it to find book-side candidates when investigating an "
            "unmatched email cash flow."
        ),
        "format": (
            "Returns `{count, rows:[…]}`; each row is `{id, bfx_trade_id, instrument, ccy, "
            "account, counterparty, side, trade_date, settl_date, gross_amt}` with ISO dates "
            "and numeric amounts. `id` is what email cash flows reference via "
            "`matched_customer_cf_id`."
        ),
    },
    "Get_Counterparty_Email_Cashflows": {
        "system_prompt": (
            "READ. Lists cash flows extracted from counterparty emails. Filters (optional, "
            "ANDed): `vendor` (ILIKE), `ccy`, `action` (BUY / SELL / SHORT SELL / BUY TO "
            "COVER), `value_date` (YYYY-MM-DD), `status` (MATCHED / UNMATCHED), `limit`. Use "
            "`status='UNMATCHED'` to list the open breaks before running Match_Cashflows or "
            "Derive_Break_Actions."
        ),
        "format": (
            "Returns `{count, rows:[…]}`; each row is `{id, amount, ccy, vendor, action, "
            "value_date, status, matched_customer_cf_id, email_ref}`. "
            "`matched_customer_cf_id` is null while the row is UNMATCHED."
        ),
    },
    "Match_Cashflows": {
        "system_prompt": (
            "WRITE (runs the reconciliation and persists results). Omit `email_ids` to attempt "
            "every UNMATCHED email row; pass `email_ids:[…]` to restrict the run. Match rules: "
            "vendor == counterparty (case-insensitive), same ccy, action == side, "
            "|amount − gross_amt| within tolerance (1.00 absolute or 1 bp), and value_date "
            "equal to trade_date or settl_date."
        ),
        "format": (
            "Returns `{summary:{considered, matched, unmatched}, matched:[…], unmatched:[…]}`. "
            "Every entry carries `{email_id, email_ref, vendor, ccy, action, amount, "
            "value_date, matched_customer_cf_id, difference, reason}` — use `reason` verbatim "
            "when explaining why a row did not match."
        ),
    },
    "Save_Counterparty_Email_Cashflow": {
        "system_prompt": (
            "WRITE (one row). Inserts a counterparty email cash flow and immediately tries to "
            "reconcile it. Required: `amount` (signed), `ccy`, `vendor`, `action` (BUY / SELL / "
            "SHORT SELL / BUY TO COVER), `value_date` (YYYY-MM-DD); optional `email_ref`. Use "
            "when a new email confirmation needs capturing."
        ),
        "format": (
            "Returns `{inserted:{…post-match row…}, match:{summary, matched, unmatched}}`. "
            "`inserted.status` tells whether it auto-reconciled (MATCHED with "
            "`matched_customer_cf_id` set); if it stayed UNMATCHED the `match` payload's "
            "`reason` explains why."
        ),
    },
    "Derive_Break_Actions": {
        "system_prompt": (
            "READ-ONLY, deterministic break analysis; takes no inputs. For every UNMATCHED "
            "email cash flow that will NOT auto-reconcile, classifies the break and suggests an "
            "ops action. Rows that would reconcile cleanly are omitted — run Match_Cashflows to "
            "actually reconcile those."
        ),
        "format": (
            "Returns `{count, actions:[…]}`; each action has a rule code (R-AMOUNT-DRIFT, "
            "R-CCY-MISMATCH, R-SIDE-MISMATCH, R-DATE-MISMATCH, R-FUZZY-VENDOR, R-NO-CANDIDATE), "
            "a human `title`/`detail`, the email row, the closest book trade, and "
            "`suggested_action`. Render as a worklist of break cards."
        ),
    },
    "Reset_Demo_Data": {
        "system_prompt": (
            "DESTRUCTIVE. Drops and recreates both cash-flow tables and re-inserts the seed "
            "rows: all email cash flows return to UNMATCHED and any rows added during the demo "
            "are removed. Only run when the user explicitly asks to reset the demo, and confirm "
            "first."
        ),
        "format": (
            "Returns `{reset:true, customer_book_cashflows:<count>, "
            "counterparty_email_cashflows:<count>, note}`. Tell the user the demo is back at "
            "its baseline."
        ),
    },
}


def tool_meta(tool_name: str, base: dict | None = None) -> dict:
    """Return MCP tool meta with the Unique AI prompt keys merged onto ``base``."""
    meta = dict(base or {})
    prompts = TOOL_PROMPTS.get(tool_name)
    if prompts:
        meta[SYSTEM_PROMPT_META_KEY] = prompts["system_prompt"]
        meta[FORMAT_INFO_META_KEY] = prompts["format"]
    return meta

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

DERIVE_BREAK_ACTIONS_DESCRIPTION = (
    "Analyse the reconciliation breaks: for every UNMATCHED counterparty (email) cash "
    "flow that will NOT auto-reconcile, explain why and suggest an operations action. "
    "Read-only and deterministic — the server-side version of the dashboard's 'smart "
    "actions'. Returns {count, actions:[…]}, one card per break with a rule code "
    "(R-AMOUNT-DRIFT, R-CCY-MISMATCH, R-SIDE-MISMATCH, R-DATE-MISMATCH, R-FUZZY-VENDOR, "
    "R-NO-CANDIDATE), a human title/detail, the email row and the closest book trade, and "
    "a suggested_action. Rows that would reconcile cleanly are omitted. Use it to produce "
    "an ops breaks worklist, or to render live smart-action cards on the canvas."
)
