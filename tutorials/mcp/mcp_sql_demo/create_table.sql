-- 1) Create the database (run while connected to the default "postgres" db)
CREATE DATABASE testdb WITH OWNER postgress;

-- 2) Connect to the new database
\c testdb

-- 3) Create the table (includes email column)
CREATE TABLE pm_positions (
  row_num       INT PRIMARY KEY,
  sleeve        TEXT NOT NULL,
  ticker        VARCHAR(10) NOT NULL,
  instrument    TEXT NOT NULL,
  direction     VARCHAR(5) NOT NULL CHECK (direction IN ('Long','Short')),
  target_weight NUMERIC(8,5) NOT NULL CHECK (target_weight BETWEEN -1 AND 1),
  position_mm   INT NOT NULL,
  email         TEXT
);

-- 4) Insert data (email filled for all except the last row)
INSERT INTO pm_positions (row_num, sleeve, ticker, instrument, direction, target_weight, position_mm, email) VALUES
(1,  'Equity Long',  'MSFT', 'Microsoft',                 'Long',  0.05,   100, 'alice@alphabet.example'),
(2,  'Equity Long',  'JNJ',  'Johnson & Johnson',         'Long',  0.04,    80, 'alice@alphabet.example'),
(3,  'Equity Long',  'UNH',  'UnitedHealth',              'Long',  0.035,   70, 'alice@alphabet.example'),
(4,  'Equity Long',  'JPM',  'JPMorgan',                  'Long',  0.04,    80, 'alice@alphabet.example'),
(5,  'Equity Long',  'CVX',  'Chevron',                   'Long',  0.03,    60, 'alice@alphabet.example'),
(6,  'Equity Beta',  'SPY',  'S&P 500 ETF',               'Long',  0.10,   200, 'alice@alphabet.example'),
(7,  'Equity Short', 'QQQ',  'Nasdaq-100 ETF',            'Short', -0.05, -100, 'alice@alphabet.example'),
(8,  'Equity Short', 'RSP',  'S&P 500 Equal-Weight',      'Short', -0.03,  -60, 'alice@alphabet.example'),
(9,  'Rates',        'IEF',  '7–10Y U.S. Treasuries',     'Long',  0.12,   240, 'alice@alphabet.example'),
(10, 'Credit',       'LQD',  'Investment Grade Credit',   'Long',  0.10,   200, 'alice@alphabet.example'),
(11, 'Alternatives', 'GLD',  'Gold',                      'Long',  0.04,    80, 'alice@alphabet.example'),
(12, 'Alternatives', 'DBC',  'Broad Commodities',         'Long',  0.04,    80, NULL);
