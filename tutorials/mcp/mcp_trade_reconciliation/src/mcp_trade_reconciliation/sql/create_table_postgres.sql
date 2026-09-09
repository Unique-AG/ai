-- PostgreSQL schema and seed data for the trade reconciliation demo.
-- The database must already exist (e.g. created by `az postgres flexible-server
-- db create` or `createdb`). Run this file against that database.
--
-- "Customer (book) cash flows" are the trades produced by our internal book.
-- "Counterparty (email) cash flows" are cash flows extracted from counterparty
-- emails (e.g. settlement instructions, confirmations). The reconciliation
-- problem is to find which counterparty (email) cash flow corresponds to
-- which customer (book) cash flow.
--
-- Matching rules (used by the reconciliation service):
--   - counterparty == vendor (case insensitive)
--   - ccy equal
--   - side == action (BUY / SELL / SHORT SELL / BUY TO COVER)
--   - |gross_amt - amount| within tolerance (default: 1.00 absolute or 1 bp)
--   - value_date equals trade_date OR settl_date (either is acceptable)
--
-- This script is idempotent: it drops and recreates the two tables so it can be
-- re-run cleanly against an existing database without leaving stale rows.

DROP TABLE IF EXISTS counterparty_email_cashflows;
DROP TABLE IF EXISTS customer_book_cashflows;

CREATE TABLE customer_book_cashflows (
  id            SERIAL PRIMARY KEY,
  bfx_trade_id  TEXT NOT NULL UNIQUE,
  instrument    TEXT NOT NULL,
  ccy           CHAR(3) NOT NULL,
  account       TEXT NOT NULL,
  counterparty  TEXT NOT NULL,
  side          TEXT NOT NULL CHECK (side IN ('BUY','SELL','SHORT SELL','BUY TO COVER')),
  trade_date    DATE NOT NULL,
  settl_date    DATE NOT NULL,
  gross_amt     NUMERIC(20,2) NOT NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX customer_book_cf_match_idx
  ON customer_book_cashflows (counterparty, ccy, side, trade_date, settl_date);

CREATE TABLE counterparty_email_cashflows (
  id                         SERIAL PRIMARY KEY,
  amount                     NUMERIC(20,2) NOT NULL,
  ccy                        CHAR(3) NOT NULL,
  vendor                     TEXT NOT NULL,
  action                     TEXT NOT NULL CHECK (action IN ('BUY','SELL','SHORT SELL','BUY TO COVER')),
  source                     TEXT NOT NULL DEFAULT 'EMAIL',
  value_date                 DATE NOT NULL,
  email_ref                  TEXT,
  status                     TEXT NOT NULL DEFAULT 'UNMATCHED'
                                CHECK (status IN ('MATCHED','UNMATCHED')),
  matched_customer_cf_id     INT REFERENCES customer_book_cashflows(id),
  difference                 NUMERIC(20,2),
  match_reason               TEXT,
  matched_at                 TIMESTAMP,
  created_at                 TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX counterparty_email_cf_match_idx
  ON counterparty_email_cashflows (vendor, ccy, action, value_date, status);

-- -------------------------------------------------------------------------
-- Seed: customer (book) cash flows (10 rows: 6 focused-demo rows + 4 extra
-- rows that match the ad-hoc emails added during a demo via
-- Save_Counterparty_Email_Cashflow).
--
-- Row purpose:
--   1. exact-match candidate (vs em-gs-msft-9001)
--   2. small-diff-match candidate (vs em-jpm-ibm-9002, matches on settl_date)
--   3. amount-too-far candidate (vs em-barclays-001)
--   4. exact-match candidate (vs em-ms-401)
--   5. no email counterpart at all (stays unmatched on the book side)
--   6. value_date mismatch candidate (vs em-date-mismatch)
--   7-10. extra book rows for ad-hoc Save_Counterparty_Email_Cashflow demos
-- -------------------------------------------------------------------------
INSERT INTO customer_book_cashflows
  (bfx_trade_id, instrument, ccy, account, counterparty, side, trade_date, settl_date, gross_amt) VALUES
  ('GS-T-8843021',           'MSFT',  'USD', 'AC-4471', 'Goldman Sachs',  'BUY',          '2026-05-23', '2026-05-26', -12948000.00),
  ('JPM-C-2026-9998',        'IBM',   'USD', 'AC-4471', 'JPMorgan',       'SELL',         '2026-05-23', '2026-05-26',   3646500.00),
  ('BAK-XSEC-AJM-3636-4847', 'RIVN',  'USD', 'AC-4471', 'Barclays Plaza', 'SHORT SELL',   '2026-05-23', '2026-05-26',   4491000.00),
  ('MS-EXEC-A2471-2026-7714','BATSY', 'EUR', 'AC-4471', 'Morgan Stanley', 'BUY',          '2026-05-23', '2026-05-26',  -1737300.00),
  ('GS-T-484247',            'TSLA',  'USD', 'AC-4471', 'Goldman Sachs',  'SHORT SELL',   '2026-05-23', '2026-05-26',   2623300.00),
  ('GS-T-484368',            'RIVN',  'USD', 'AC-4471', 'Goldman Sachs',  'BUY TO COVER', '2026-05-23', '2026-05-26',  -7901300.00),
  -- Extra book rows that match the ad-hoc emails inserted via Save_Counterparty_Email_Cashflow.
  ('GS-T-9024-MSFT',         'MSFT',  'USD', 'AC-4471', 'Goldman Sachs',  'BUY',          '2026-05-23', '2026-05-26',  12948000.00),
  ('JPM-C-9025-JPY',         'NTT',   'JPY', 'AC-4471', 'JPMorgan',       'BUY TO COVER', '2026-05-22', '2026-05-27', 144300000.00),
  ('MS-EXEC-9026-MS',        'XOM',   'USD', 'AC-4471', 'Morgan Stanley', 'BUY',          '2026-05-23', '2026-05-26',   8662000.00),
  ('MS-EXEC-9027-MS',        'CRM',   'USD', 'AC-4471', 'Morgan Stanley', 'BUY',          '2026-05-23', '2026-05-26',   5261000.00),
  -- Derivatives: cash flows from FX options (premiums) and Total Return Swaps (reset /
  -- funding legs). Same reconciliation semantics — a premium or swap-leg payment is just
  -- a cash flow with a counterparty, ccy, direction and value date.
  --  11. FX option premium paid (clean email match on trade_date)
  --  12. FX option premium in JPY — email arrives 150,000 short (sales margin) -> drift break
  --  13. TRS equity-leg reset receipt (clean email match on settl_date)
  --  14. TRS funding-leg payment in USD — email confirms in GBP -> ccy-mismatch break
  ('UBS-OPT-77012',          'EURUSD 3M CALL K=1.0850',        'USD', 'AC-4471', 'UBS',            'BUY',  '2026-05-23', '2026-05-27',   -845000.00),
  ('GS-OPT-77104',           'USDJPY 6M PUT K=152.00',         'JPY', 'AC-4471', 'Goldman Sachs',  'BUY',  '2026-05-23', '2026-05-27', -98500000.00),
  ('MS-TRS-2026-5501',       'TRS SX5E TOTAL RETURN LEG',      'EUR', 'AC-4471', 'Morgan Stanley', 'SELL', '2026-05-23', '2026-05-29',   2184500.00),
  ('BARC-TRS-2026-5502',     'TRS SPX FUNDING LEG SOFR+85bp',  'USD', 'AC-4471', 'Barclays Plaza', 'BUY',  '2026-05-23', '2026-05-29',   -412750.00);

-- -------------------------------------------------------------------------
-- Seed: counterparty (email) cash flows (6 rows)
--
-- Row purpose:
--   1. exact match for customer row #1 (trade_date)
--   2. $50 diff vs customer row #2, matches on settl_date
--   3. amount outside tolerance vs customer row #3 ($75,700 vs $449 tol)
--   4. exact match for customer row #4
--   5. orphan vendor/side: JPMorgan BUY USD has no book counterpart
--   6. matches vendor/ccy/side/amount of customer row #6, but value_date
--      does not equal either trade_date or settl_date
-- -------------------------------------------------------------------------
INSERT INTO counterparty_email_cashflows
  (amount, ccy, vendor, action, value_date, email_ref) VALUES
  (-12948000.00, 'USD', 'Goldman Sachs',  'BUY',          '2026-05-23', 'em-gs-msft-9001'),
  (  3646450.00, 'USD', 'JPMorgan',       'SELL',         '2026-05-26', 'em-jpm-ibm-9002'),
  (  4415300.00, 'USD', 'Barclays Plaza', 'SHORT SELL',   '2026-05-23', 'em-barclays-001'),
  ( -1737300.00, 'EUR', 'Morgan Stanley', 'BUY',          '2026-05-23', 'em-ms-401'),
  (   555000.00, 'USD', 'JPMorgan',       'BUY',          '2026-05-23', 'em-orphan-jpm'),
  ( -7901300.00, 'USD', 'Goldman Sachs',  'BUY TO COVER', '2026-05-30', 'em-date-mismatch'),
  -- Derivative confirmations:
  --   7. FX option premium — exact match for UBS-OPT-77012 (trade_date)
  --   8. FX option premium 150,000 JPY short vs GS-OPT-77104 (tol ~9,850) -> amount drift
  --   9. TRS reset receipt — exact match for MS-TRS-2026-5501 (settl_date)
  --  10. TRS funding leg confirmed in GBP (book leg is USD) -> ccy mismatch, missing FX leg
  (  -845000.00, 'USD', 'UBS',            'BUY',          '2026-05-23', 'em-ubs-fxopt-9101'),
  (-98350000.00, 'JPY', 'Goldman Sachs',  'BUY',          '2026-05-23', 'em-gs-fxopt-9102'),
  (  2184500.00, 'EUR', 'Morgan Stanley', 'SELL',         '2026-05-29', 'em-ms-trs-9103'),
  (  -412750.00, 'GBP', 'Barclays Plaza', 'BUY',          '2026-05-29', 'em-barc-trs-9104');
