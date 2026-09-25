-- PostgreSQL schema and seed data for the Advisory MCP's "house_views" domain.
-- Mirrors mcp_sql_demo: the data that the n8n workflow held inline in JavaScript
-- now lives in real tables. Database must already exist (e.g. created by
-- `az postgres flexible-server db create`). Idempotent: safe to run repeatedly.
-- One sql/*.sql file per Advisory domain; deploy_pg.sh seeds them all.

-- ---------------------------------------------------------------------------
-- Bank-wide metadata shared by every tool (single row).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS house_view_meta (
  id          INT  PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  house       TEXT NOT NULL,
  as_of       DATE NOT NULL,
  valid_until DATE NOT NULL
);

INSERT INTO house_view_meta (id, house, as_of, valid_until) VALUES
  (1, 'ABC Wealth Management — CIO Office', '2026-06-20', '2026-09-30')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- [HV 1a] get_house_view — per-asset-class stance.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS house_view (
  position    INT  PRIMARY KEY,            -- display order
  asset_class TEXT NOT NULL,
  stance      TEXT NOT NULL,
  score       INT  NOT NULL,
  rationale   TEXT NOT NULL
);

INSERT INTO house_view (position, asset_class, stance, score, rationale) VALUES
  (1, 'Equities',     'Neutral',                              0, 'Favour quality and low-volatility names over cyclicals; valuations full but earnings resilient.'),
  (2, 'Fixed income', 'Overweight',                           1, 'Attractive yields in high-grade credit; prefer short-to-intermediate duration.'),
  (3, 'Alternatives', 'Selective',                            1, 'Gold and market-neutral strategies for diversification and drawdown control.'),
  (4, 'FX',           'CHF strength expected to persist',     0, 'Hedge non-CHF exposure for CHF-reference clients.'),
  (5, 'Cash',         'Neutral',                              0, 'Hold a modest buffer; money-market yields still adequate.')
ON CONFLICT (position) DO NOTHING;

-- ---------------------------------------------------------------------------
-- [HV 1b] get_cio_themes — CIO investment themes / convictions.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cio_themes (
  position   INT  PRIMARY KEY,
  theme      TEXT NOT NULL,
  horizon    TEXT NOT NULL,
  conviction TEXT NOT NULL,
  rationale  TEXT NOT NULL
);

INSERT INTO cio_themes (position, theme, horizon, conviction, rationale) VALUES
  (1, 'Quality over cyclicals',         '6-12m',     'High',   'Late-cycle: prefer strong balance sheets, stable cash flows, low leverage.'),
  (2, 'Lock in high-grade yield',        '6-18m',     'High',   'Investment-grade credit yields near multi-year highs; extend gradually from cash.'),
  (3, 'Short-to-intermediate duration',  '3-9m',      'Medium', 'Curve uncertainty; avoid long-duration concentration.'),
  (4, 'Gold as portfolio insurance',     '12m+',      'Medium', 'Diversifier versus equity drawdowns and geopolitical risk.'),
  (5, 'CHF strength',                    '6-12m',     'Medium', 'Hedge non-CHF exposure for CHF-reference mandates.'),
  (6, 'Sustainable / ESG overlay',       'strategic', 'Medium', 'Client demand and regulatory direction; available as an overlay.')
ON CONFLICT (position) DO NOTHING;

-- ---------------------------------------------------------------------------
-- [HV 1c] get_tactical_calls — tactical allocation calls.
-- "call" is non-reserved in PostgreSQL, but we quote it everywhere to be safe.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tactical_calls (
  position   INT  PRIMARY KEY,
  dimension  TEXT NOT NULL,
  "call"     TEXT NOT NULL,
  detail     TEXT NOT NULL,
  magnitude  TEXT NOT NULL,
  conviction TEXT NOT NULL,
  rationale  TEXT NOT NULL
);

INSERT INTO tactical_calls (position, dimension, "call", detail, magnitude, conviction, rationale) VALUES
  (1, 'Equity regions', 'Overweight',  'US quality & Swiss defensives',    '+', 'Medium', 'Earnings resilience, lower beta.'),
  (2, 'Equity regions', 'Underweight', 'Emerging markets ex-Asia',         '-', 'Medium', 'FX and policy risk.'),
  (3, 'Credit',         'Overweight',  'Investment-grade, short duration', '+', 'High',   'Yield with limited rate risk.'),
  (4, 'Duration',       'Underweight', 'Long government bonds',            '-', 'Medium', 'Curve uncertainty.'),
  (5, 'Alternatives',   'Overweight',  'Gold + market neutral',            '+', 'Medium', 'Diversification, drawdown control.'),
  (6, 'FX',             'Hedge',       'Non-CHF for CHF mandates',         '=', 'Medium', 'Expected CHF strength.')
ON CONFLICT (position) DO NOTHING;
