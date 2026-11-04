"""Trade reconciliation service.

Reads/saves the two cash-flow tables and reconciles counterparty (email) cash
flows against customer (book) cash flows.

Matching rules (all must hold for a row to be considered a match):
    * counterparty matches vendor (case-insensitive, trimmed)
    * ccy is equal
    * side equals action
    * |gross_amt - amount| <= tolerance (default: max(1.00, 1 bp of |gross_amt|))
    * value_date equals trade_date OR settl_date (either side accepted)

If multiple customer rows are eligible for the same email row, the one with the
smallest absolute amount difference wins. Already-matched customer rows cannot
be reused.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from difflib import SequenceMatcher
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5432"))
DB_NAME = os.getenv("PGDATABASE", "reconciliationdb")
DB_USER = os.getenv("PGUSER", "postgres")
DB_PASSWORD = os.getenv("PGPASSWORD", "postgres")

CUSTOMER_TABLE = "customer_book_cashflows"
COUNTERPARTY_TABLE = "counterparty_email_cashflows"

# Bundled schema + seed used to restore the demo to a known baseline. Lives at
# src/mcp_trade_reconciliation/sql/create_table_postgres.sql (two levels up).
_SEED_SQL_PATH = Path(__file__).resolve().parent.parent / "sql" / "create_table_postgres.sql"

ALLOWED_SIDES = {"BUY", "SELL", "SHORT SELL", "BUY TO COVER"}

# Default matching tolerance: the larger of an absolute floor or 1 basis point
# of the book amount. Keeps tiny rows from being over-restrictive while big
# trades still get tight matching.
_ABSOLUTE_TOLERANCE = Decimal("1.00")
_RELATIVE_TOLERANCE_BPS = Decimal("1")  # 1 bp == 0.0001


@dataclass
class MatchOutcome:
    """Result of attempting to match a single email cash flow."""

    email_id: int
    matched: bool
    customer_cf_id: int | None
    difference: Decimal | None
    reason: str


def _get_connection() -> PgConnection:
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


@contextmanager
def _readonly_connection() -> Iterator[PgConnection]:
    """Yield a connection in read-only mode.

    psycopg2 forbids ``set_session`` once a transaction is open, so we set the
    session flags *before* any query is executed and let the connection close
    on exit (no need to flip the flag back).
    """
    conn = _get_connection()
    try:
        conn.set_session(readonly=True)
        yield conn
    finally:
        conn.close()


@contextmanager
def _readwrite_connection() -> Iterator[PgConnection]:
    """Yield a writable connection that commits on success and rolls back on error."""
    conn = _get_connection()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _tolerance_for(book_amount: Decimal) -> Decimal:
    """Compute the amount tolerance for a book row."""
    relative = (abs(book_amount) * _RELATIVE_TOLERANCE_BPS) / Decimal("10000")
    return max(_ABSOLUTE_TOLERANCE, relative)


def _norm(value: str | None) -> str:
    return (value or "").strip().casefold()


def _parse_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def _row_to_jsonable(row: dict[str, Any]) -> dict[str, Any]:
    """Convert psycopg2 row types into JSON-friendly primitives."""
    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, (date, datetime)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def list_customer_book_cashflows(
    counterparty: str | None = None,
    ccy: str | None = None,
    side: str | None = None,
    trade_date: str | date | None = None,
    settl_date: str | date | None = None,
    instrument: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return rows from ``customer_book_cashflows`` filtered by the given args."""
    clauses: list[str] = []
    params: list[Any] = []
    if counterparty:
        clauses.append("counterparty ILIKE %s")
        params.append(counterparty)
    if ccy:
        clauses.append("ccy = %s")
        params.append(ccy.upper())
    if side:
        clauses.append("side = %s")
        params.append(side.upper())
    if trade_date:
        clauses.append("trade_date = %s")
        params.append(_parse_date(trade_date))
    if settl_date:
        clauses.append("settl_date = %s")
        params.append(_parse_date(settl_date))
    if instrument:
        clauses.append("instrument ILIKE %s")
        params.append(instrument)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        f"SELECT * FROM {CUSTOMER_TABLE} {where} "
        f"ORDER BY trade_date DESC, id ASC LIMIT %s"
    )
    params.append(limit)

    with _readonly_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [_row_to_jsonable(r) for r in rows]


def list_counterparty_email_cashflows(
    vendor: str | None = None,
    ccy: str | None = None,
    action: str | None = None,
    value_date: str | date | None = None,
    status: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return rows from ``counterparty_email_cashflows`` filtered by the given args."""
    clauses: list[str] = []
    params: list[Any] = []
    if vendor:
        clauses.append("vendor ILIKE %s")
        params.append(vendor)
    if ccy:
        clauses.append("ccy = %s")
        params.append(ccy.upper())
    if action:
        clauses.append("action = %s")
        params.append(action.upper())
    if value_date:
        clauses.append("value_date = %s")
        params.append(_parse_date(value_date))
    if status:
        clauses.append("status = %s")
        params.append(status.upper())

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        f"SELECT * FROM {COUNTERPARTY_TABLE} {where} "
        f"ORDER BY value_date DESC, id ASC LIMIT %s"
    )
    params.append(limit)

    with _readonly_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [_row_to_jsonable(r) for r in rows]


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


def _find_match_for_email(
    email_row: dict[str, Any],
    customer_rows: list[dict[str, Any]],
    already_matched_customer_ids: set[int],
) -> MatchOutcome:
    """Pick the best customer row for one email row, or report why none fits."""
    email_id: int = email_row["id"]
    email_amount: Decimal = email_row["amount"]
    email_ccy: str = email_row["ccy"]
    email_vendor: str = email_row["vendor"]
    email_action: str = email_row["action"]
    email_date: date = email_row["value_date"]

    # Whittle down candidates with progressively stricter checks so we can
    # report a useful reason when nothing fits.
    same_vendor = [
        r for r in customer_rows if _norm(r["counterparty"]) == _norm(email_vendor)
    ]
    if not same_vendor:
        return MatchOutcome(
            email_id=email_id,
            matched=False,
            customer_cf_id=None,
            difference=None,
            reason=f"no customer cash flow with counterparty={email_vendor!r}",
        )

    same_ccy = [r for r in same_vendor if r["ccy"] == email_ccy]
    if not same_ccy:
        return MatchOutcome(
            email_id=email_id,
            matched=False,
            customer_cf_id=None,
            difference=None,
            reason=f"vendor {email_vendor!r} found but no row with ccy={email_ccy}",
        )

    same_action = [r for r in same_ccy if r["side"] == email_action]
    if not same_action:
        return MatchOutcome(
            email_id=email_id,
            matched=False,
            customer_cf_id=None,
            difference=None,
            reason=(
                f"vendor/ccy found but no row with side={email_action!r} "
                f"(observed sides: {sorted({r['side'] for r in same_ccy})})"
            ),
        )

    same_date = [
        r
        for r in same_action
        if email_date == r["trade_date"] or email_date == r["settl_date"]
    ]
    if not same_date:
        return MatchOutcome(
            email_id=email_id,
            matched=False,
            customer_cf_id=None,
            difference=None,
            reason=(
                f"vendor/ccy/side found but value_date={email_date.isoformat()} "
                "does not equal any trade_date or settl_date"
            ),
        )

    # Amount must be within tolerance, prefer the closest one. Skip rows that
    # have already been matched in this run.
    best: tuple[dict[str, Any], Decimal] | None = None
    rejected_diffs: list[tuple[str, Decimal, Decimal]] = []
    for r in same_date:
        if r["id"] in already_matched_customer_ids:
            continue
        diff = r["gross_amt"] - email_amount
        tol = _tolerance_for(r["gross_amt"])
        if abs(diff) <= tol:
            if best is None or abs(diff) < abs(best[1]):
                best = (r, diff)
        else:
            rejected_diffs.append((r["bfx_trade_id"], diff, tol))

    if best is None:
        if rejected_diffs:
            sample = ", ".join(
                f"{tid} diff={float(d):.2f} tol={float(t):.2f}"
                for tid, d, t in rejected_diffs[:3]
            )
            reason = (
                "vendor/ccy/side/date matched but amounts outside tolerance "
                f"(closest: {sample})"
            )
        else:
            reason = (
                "vendor/ccy/side/date matched but all candidate customer rows "
                "are already matched to another email cash flow"
            )
        return MatchOutcome(
            email_id=email_id,
            matched=False,
            customer_cf_id=None,
            difference=None,
            reason=reason,
        )

    customer_row, diff = best
    on_trade_date = email_date == customer_row["trade_date"]
    on_settl_date = email_date == customer_row["settl_date"]
    date_field = (
        "trade_date"
        if on_trade_date and not on_settl_date
        else "settl_date"
        if on_settl_date and not on_trade_date
        else "trade_date==settl_date"
    )
    reason = (
        f"matched on counterparty/ccy/side, value_date={email_date.isoformat()} "
        f"({date_field}), |diff|={float(abs(diff)):.2f} "
        f"<= tol={float(_tolerance_for(customer_row['gross_amt'])):.2f}"
    )
    return MatchOutcome(
        email_id=email_id,
        matched=True,
        customer_cf_id=customer_row["id"],
        difference=diff,
        reason=reason,
    )


def _load_for_matching(
    conn,
    email_ids: list[int] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[int]]:
    """Load the candidate email and customer rows plus already-used customer ids."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if email_ids is None:
            cur.execute(
                f"SELECT * FROM {COUNTERPARTY_TABLE} WHERE status = 'UNMATCHED' "
                "ORDER BY id ASC"
            )
        else:
            # ORDER BY id ASC so processing order is deterministic across runs
            # (mirrors the default UNMATCHED path); otherwise competing email
            # rows could claim the same book line in a different order each time.
            cur.execute(
                f"SELECT * FROM {COUNTERPARTY_TABLE} WHERE id = ANY(%s) ORDER BY id ASC",
                (email_ids,),
            )
        email_rows = cur.fetchall()

        # FOR UPDATE locks the book rows for the duration of this transaction so
        # two concurrent match runs cannot both reserve the same customer cash
        # flow (the in-memory reservation below is not visible across sessions).
        cur.execute(f"SELECT * FROM {CUSTOMER_TABLE} ORDER BY id ASC FOR UPDATE")
        customer_rows = cur.fetchall()

        # Reserve book rows that are already linked to *other* email rows. The
        # email rows we are about to (re)match must not have their own current
        # link counted as reserved, otherwise re-running the matcher for an
        # already-MATCHED row would find no eligible book row and clear the
        # match. Excluding the rows being processed makes re-matching idempotent.
        processed_ids = [r["id"] for r in email_rows]
        if processed_ids:
            cur.execute(
                f"SELECT matched_customer_cf_id FROM {COUNTERPARTY_TABLE} "
                "WHERE matched_customer_cf_id IS NOT NULL AND id <> ALL(%s)",
                (processed_ids,),
            )
        else:
            cur.execute(
                f"SELECT matched_customer_cf_id FROM {COUNTERPARTY_TABLE} "
                "WHERE matched_customer_cf_id IS NOT NULL"
            )
        already_matched = {
            r["matched_customer_cf_id"] for r in cur.fetchall() if r["matched_customer_cf_id"] is not None
        }
    return email_rows, customer_rows, already_matched


def _persist_match(conn, outcome: MatchOutcome) -> None:
    with conn.cursor() as cur:
        # Only stamp matched_at when the row actually matched; unmatched rows
        # must keep a NULL timestamp instead of a misleading "recently matched".
        cur.execute(
            f"UPDATE {COUNTERPARTY_TABLE} SET "
            "status = %s, matched_customer_cf_id = %s, difference = %s, "
            "match_reason = %s, matched_at = CASE WHEN %s THEN NOW() ELSE NULL END "
            "WHERE id = %s",
            (
                "MATCHED" if outcome.matched else "UNMATCHED",
                outcome.customer_cf_id,
                outcome.difference,
                outcome.reason,
                outcome.matched,
                outcome.email_id,
            ),
        )


def match_cashflows(email_ids: list[int] | None = None) -> dict[str, Any]:
    """Reconcile counterparty email cash flows against the customer book.

    Args:
        email_ids: When provided, only attempt to match those email rows. When
            ``None``, attempts to match every email row currently in ``UNMATCHED``
            status.

    Returns:
        A dict with ``matched`` and ``unmatched`` lists of outcomes plus a
        summary.
    """
    matched: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []

    with _readwrite_connection() as conn:
        email_rows, customer_rows, used_customer_ids = _load_for_matching(conn, email_ids)

        for email_row in email_rows:
            outcome = _find_match_for_email(email_row, customer_rows, used_customer_ids)
            if outcome.matched and outcome.customer_cf_id is not None:
                used_customer_ids.add(outcome.customer_cf_id)
            _persist_match(conn, outcome)

            entry = {
                "email_id": outcome.email_id,
                "email_ref": email_row.get("email_ref"),
                "vendor": email_row["vendor"],
                "ccy": email_row["ccy"],
                "action": email_row["action"],
                "amount": float(email_row["amount"]),
                "value_date": email_row["value_date"].isoformat(),
                "matched_customer_cf_id": outcome.customer_cf_id,
                "difference": float(outcome.difference) if outcome.difference is not None else None,
                "reason": outcome.reason,
            }
            (matched if outcome.matched else unmatched).append(entry)

    return {
        "summary": {
            "considered": len(email_rows),
            "matched": len(matched),
            "unmatched": len(unmatched),
        },
        "matched": matched,
        "unmatched": unmatched,
    }


# ---------------------------------------------------------------------------
# Save (insert + auto-match)
# ---------------------------------------------------------------------------


def save_counterparty_email_cashflow(
    amount: float | Decimal,
    ccy: str,
    vendor: str,
    action: str,
    value_date: str | date,
    email_ref: str | None = None,
) -> dict[str, Any]:
    """Insert a new counterparty email cash flow and immediately attempt to match it.

    Returns the inserted row plus the match outcome.
    """
    if action.upper() not in ALLOWED_SIDES:
        raise ValueError(
            f"action={action!r} must be one of {sorted(ALLOWED_SIDES)}"
        )
    amount_dec = Decimal(str(amount))
    value_date_d = _parse_date(value_date)

    with _readwrite_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"INSERT INTO {COUNTERPARTY_TABLE} "
            "(amount, ccy, vendor, action, value_date, email_ref) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING *",
            (
                amount_dec,
                ccy.upper(),
                vendor,
                action.upper(),
                value_date_d,
                email_ref,
            ),
        )
        inserted = cur.fetchone()

    # Run matching only for the newly inserted row so we get a focused outcome.
    match_result = match_cashflows(email_ids=[inserted["id"]])

    # Re-read the row so `inserted` reflects the post-match state (status,
    # matched_customer_cf_id, difference) rather than the pre-match RETURNING row.
    with _readonly_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"SELECT * FROM {COUNTERPARTY_TABLE} WHERE id = %s", (inserted["id"],))
        refreshed = cur.fetchone()

    return {
        "inserted": _row_to_jsonable(refreshed or inserted),
        "match": match_result,
    }


# ---------------------------------------------------------------------------
# Demo reset
# ---------------------------------------------------------------------------


def reset_demo_data() -> dict[str, Any]:
    """Restore both cash-flow tables to the demo baseline.

    Executes the bundled ``create_table_postgres.sql`` script in a single
    transaction: it drops and recreates ``customer_book_cashflows`` and
    ``counterparty_email_cashflows`` and re-inserts the seed rows. After a reset
    every counterparty (email) cash flow is back in ``UNMATCHED`` status (and any
    rows added during the demo via ``Save_Counterparty_Email_Cashflow`` are
    removed), so a demo can show the reconciliation happening live again.

    Returns:
        A dict with the row counts of both tables after the reset.
    """
    if not _SEED_SQL_PATH.is_file():
        raise FileNotFoundError(f"Seed SQL not found at {_SEED_SQL_PATH}")
    sql_text = _SEED_SQL_PATH.read_text(encoding="utf-8")

    with _readwrite_connection() as conn, conn.cursor() as cur:
        # Execute each statement separately; relying on one multi-statement
        # cursor.execute is driver/version-dependent. The surrounding connection
        # context still keeps the full reset transactional.
        for statement in sql_text.split(";"):
            if any(line.strip() and not line.strip().startswith("--") for line in statement.splitlines()):
                cur.execute(statement)
        cur.execute(f"SELECT COUNT(*) FROM {CUSTOMER_TABLE}")
        customer_count = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {COUNTERPARTY_TABLE}")
        counterparty_count = cur.fetchone()[0]

    return {
        "reset": True,
        "customer_book_cashflows": customer_count,
        "counterparty_email_cashflows": counterparty_count,
        "note": "Demo restored to baseline; all counterparty (email) cash flows are UNMATCHED.",
    }


# ---------------------------------------------------------------------------
# Break analysis ("smart actions") — server-side, deterministic
# ---------------------------------------------------------------------------
# For every UNMATCHED email row that will NOT auto-reconcile, explain WHY and
# suggest an ops action. This is the reliable replacement for the old in-page
# JavaScript fuzzy engine (the HTML sandbox strips scripts): the same rules run
# here (R-AMOUNT-DRIFT / R-CCY-MISMATCH / R-SIDE-MISMATCH / R-DATE-MISMATCH /
# R-FUZZY-VENDOR / R-NO-CANDIDATE), so the dashboard/agent can render live cards.

_VENDOR_SIM_THRESHOLD = 0.50  # SequenceMatcher ratio to call two names "similar"


def _vendor_similarity(a: str | None, b: str | None) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _closest_by_amount(rows: list[dict[str, Any]], amount: Decimal) -> dict[str, Any] | None:
    """The row whose gross_amt is nearest the email amount (the likeliest intended trade)."""
    return min(rows, key=lambda r: abs(r["gross_amt"] - amount)) if rows else None


def _break_card(
    rule: str, title: str, email_row: dict[str, Any], detail: str,
    suggested_action: str, book_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    card: dict[str, Any] = {
        "rule": rule,
        "title": title,
        "email_id": email_row["id"],
        "vendor": email_row["vendor"],
        "email_amount": float(email_row["amount"]),
        "email_ccy": email_row["ccy"],
        "email_action": email_row["action"],
        "detail": detail,
        "suggested_action": suggested_action,
    }
    if book_row is not None:
        card.update({
            "book_trade_ref": book_row["bfx_trade_id"],
            "book_instrument": book_row["instrument"],
            "book_amount": float(book_row["gross_amt"]),
            "book_ccy": book_row["ccy"],
            "book_side": book_row["side"],
        })
    return card


def _classify_break(
    email_row: dict[str, Any],
    book_rows: list[dict[str, Any]],
    used_customer_ids: set[int] | None = None,
) -> dict[str, Any]:
    """Explain, in priority order, the first dimension on which an email row breaks.

    Only unreserved book rows are considered — citing a line already linked to
    another email (or claimed earlier in the same run) would misstate which
    trade is actually in contention. With every candidate reserved the cascade
    falls through to R-NO-CANDIDATE, which is the truthful outcome.
    """
    if used_customer_ids:
        book_rows = [r for r in book_rows if r["id"] not in used_customer_ids]
    ev, eccy, eact, eamt = (
        email_row["vendor"], email_row["ccy"], email_row["action"], email_row["amount"],
    )
    same_vendor = [r for r in book_rows if _norm(r["counterparty"]) == _norm(ev)]
    if not same_vendor:
        fuzzy = [r for r in book_rows if _vendor_similarity(ev, r["counterparty"]) >= _VENDOR_SIM_THRESHOLD]
        cand = _closest_by_amount(fuzzy, eamt)
        if cand is not None:
            return _break_card(
                "R-FUZZY-VENDOR", "Counterparty name doesn't match exactly", email_row,
                f"No book trade for counterparty '{ev}'. Closest by name is '{cand['counterparty']}' "
                f"(trade {cand['bfx_trade_id']}) — likely a spelling/alias mismatch on the confirm.",
                "Confirm the counterparty alias / legal entity, then re-run the matcher.", cand)
        return _break_card(
            "R-NO-CANDIDATE", "No matching book trade", email_row,
            f"No book trade found for counterparty '{ev}' — the email may reference a trade not yet "
            "booked, or a different desk.",
            "Check whether the trade is booked; chase the desk or the counterparty confirm.")

    same_ccy = [r for r in same_vendor if r["ccy"] == eccy]
    if not same_ccy:
        cand = _closest_by_amount(same_vendor, eamt)
        return _break_card(
            "R-CCY-MISMATCH", "Currency mismatch on same counterparty", email_row,
            f"Email is in {eccy} but the closest book trade for {ev} ({cand['bfx_trade_id']}) is in "
            f"{cand['ccy']} — possible missing FX leg or wrong base ccy on the confirm.",
            "Request the FX leg / confirm the base currency on the counterparty email.", cand)

    same_side = [r for r in same_ccy if r["side"] == eact]
    if not same_side:
        cand = _closest_by_amount(same_ccy, eamt)
        return _break_card(
            "R-SIDE-MISMATCH", "Side/action mismatch on same counterparty", email_row,
            f"Email action is {eact} but the closest book trade for {ev} ({cand['bfx_trade_id']}) is "
            f"{cand['side']}.",
            "Verify the direction with the counterparty; correct the confirm or the booking.", cand)

    # Date is its own cascade tier, mirroring _find_match_for_email's precedence
    # (date filter before amount tolerance): only when NO same-side row lines up
    # on date is the break a date mismatch — otherwise the closest date-matching
    # row is the line in contention and the drift is on amount.
    edate = email_row["value_date"]
    same_date = [r for r in same_side if edate in (r["trade_date"], r["settl_date"])]
    if not same_date:
        cand = _closest_by_amount(same_side, eamt)
        return _break_card(
            "R-DATE-MISMATCH", "Value date doesn't line up", email_row,
            f"Email value_date {edate.isoformat()} doesn't equal the trade "
            f"({cand['trade_date'].isoformat()}) or settlement ({cand['settl_date'].isoformat()}) date "
            f"of {cand['bfx_trade_id']}.",
            "Confirm the settlement date — a T+ mismatch or an amended settl date is likely.", cand)

    cand = _closest_by_amount(same_date, eamt)
    diff = cand["gross_amt"] - eamt
    pct = (abs(diff) / abs(cand["gross_amt"]) * 100) if cand["gross_amt"] else Decimal(0)
    return _break_card(
        "R-AMOUNT-DRIFT", "Amount close but not exact", email_row,
        f"Email {float(eamt):,.2f} {eccy} vs book {float(cand['gross_amt']):,.2f} {cand['ccy']} "
        f"({cand['bfx_trade_id']}) — drift {float(abs(diff)):,.2f} ({float(pct):.2f}%). Could be a fee, "
        "an FX cut, or quote-to-fill slippage.",
        "Check net-vs-gross / the fee schedule; if within policy, book the adjustment for review.", cand)


def derive_break_actions() -> dict[str, Any]:
    """Classify every UNMATCHED email row that will NOT auto-match into a break action card.

    Read-only. Rows that WOULD reconcile on ``Match_Cashflows`` are skipped (they're not
    breaks). Returns ``{count, actions:[…]}`` where each action carries a rule code, a
    human title/detail, the email and closest book trade, and a suggested ops action.
    """
    with _readonly_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"SELECT * FROM {COUNTERPARTY_TABLE} WHERE status = 'UNMATCHED' ORDER BY id ASC")
        email_rows = cur.fetchall()
        cur.execute(f"SELECT * FROM {CUSTOMER_TABLE} ORDER BY id ASC")
        customer_rows = cur.fetchall()
        # Book rows already linked to MATCHED email rows are not available to the
        # rows analysed here — same reservation as _load_for_matching (read-only,
        # so no FOR UPDATE; the emails in scope are UNMATCHED and hold no links).
        cur.execute(
            f"SELECT matched_customer_cf_id FROM {COUNTERPARTY_TABLE} "
            "WHERE matched_customer_cf_id IS NOT NULL"
        )
        used_customer_ids = {
            r["matched_customer_cf_id"] for r in cur.fetchall() if r["matched_customer_cf_id"] is not None
        }

    actions: list[dict[str, Any]] = []
    for email_row in email_rows:
        # Skip rows that would reconcile cleanly on Match_Cashflows — those aren't
        # breaks. Reserve the book row each would claim (same id order and
        # first-wins semantics as match_cashflows) so a later email competing for
        # the same book line is reported as the break it really is.
        outcome = _find_match_for_email(email_row, customer_rows, used_customer_ids)
        if outcome.matched:
            if outcome.customer_cf_id is not None:
                used_customer_ids.add(outcome.customer_cf_id)
            continue
        actions.append(_classify_break(email_row, customer_rows, used_customer_ids))
    return {"count": len(actions), "actions": actions}
