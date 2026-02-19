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

-- 4) Insert data (alice@alphabet.example and tin.oroz@unique-ai-academy.com)
INSERT INTO pm_positions (row_num, sleeve, ticker, instrument, direction, target_weight, position_mm, email) VALUES
-- Alice's positions 
(1,  'Equity Long',  'MSFT', 'Microsoft',                 'Long',  0.05,   100, 'alice@alphabet.example'),
(2,  'Equity Long',  'JNJ',  'Johnson & Johnson',         'Long',  0.04,    80, 'alice@alphabet.example'),
(3,  'Equity Long',  'UNH',  'UnitedHealth',              'Long',  0.035,   70, 'alice@alphabet.example'),

-- Tin's positions
(4,  'Equity Beta',  'SPY',  'S&P 500 ETF',               'Long',  0.15,   300, 'tin.oroz@unique-ai-academy.com'),
(5,  'Equity Long',  'AAPL', 'Apple Inc',                 'Long',  0.08,   160, 'tin.oroz@unique-ai-academy.com'),
(6,  'Equity Long',  'NVDA', 'NVIDIA',                    'Long',  0.06,   120, 'tin.oroz@unique-ai-academy.com'),
(7,  'Equity Short', 'QQQ',  'Nasdaq-100 ETF',            'Short', -0.04,  -80, 'tin.oroz@unique-ai-academy.com'),
(8,  'Rates',        'TLT',  '20+ Year Treasury Bond',    'Long',  0.10,   200, 'tin.oroz@unique-ai-academy.com'),
(9,  'Alternatives', 'GLD',  'Gold',                      'Long',  0.05,   100, 'tin.oroz@unique-ai-academy.com'),
(10, 'Equity Beta',  'VOO',  'Vanguard S&P 500 ETF',      'Long',  0.08,   160, 'tin.oroz@unique-ai-academy.com');
