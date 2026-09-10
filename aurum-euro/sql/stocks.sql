-- European listed issuers on euro-area regulated markets.
-- Prices stay empty until a venue republication right exists.
CREATE TABLE IF NOT EXISTS venues (
  mic TEXT PRIMARY KEY,
  geo TEXT NOT NULL,
  market TEXT NOT NULL,
  operator TEXT,
  official_list_url TEXT,
  oam_url TEXT
);
CREATE TABLE IF NOT EXISTS issuers (
  lei TEXT PRIMARY KEY,
  legal_name TEXT NOT NULL,
  registered_seat_geo TEXT,
  nace TEXT,
  first_seen TEXT,
  status TEXT
);
CREATE TABLE IF NOT EXISTS listings (
  listing_id TEXT PRIMARY KEY,
  lei TEXT NOT NULL,
  isin TEXT,
  mic TEXT NOT NULL,
  ticker TEXT,
  listed_from TEXT,
  listed_to TEXT,
  status TEXT,
  FOREIGN KEY(lei) REFERENCES issuers(lei),
  FOREIGN KEY(mic) REFERENCES venues(mic)
);
CREATE TABLE IF NOT EXISTS oam_filings (
  id INTEGER PRIMARY KEY,
  lei TEXT NOT NULL,
  period TEXT,
  form TEXT,
  oam_url TEXT,
  retrieved_at TEXT
);
CREATE TABLE IF NOT EXISTS market_prints (
  id INTEGER PRIMARY KEY,
  listing_id TEXT NOT NULL,
  print_date TEXT NOT NULL,
  close_eur REAL,
  shares REAL,
  source TEXT,
  licence_note TEXT
);
