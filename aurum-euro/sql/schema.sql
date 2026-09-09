-- Aurum Euro canonical store. Source observations are immutable.
-- Derived €Au rows live in au_observations. Never overwrite observations_raw.

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL, -- eurostat | stoxx | gold
  homepage TEXT,
  license_note TEXT
);

CREATE TABLE IF NOT EXISTS datasets (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(id),
  code TEXT NOT NULL,
  title TEXT,
  frequency TEXT,
  registry_json TEXT
);

CREATE TABLE IF NOT EXISTS dataset_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dataset_id TEXT NOT NULL REFERENCES datasets(id),
  version TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  is_current INTEGER NOT NULL DEFAULT 1,
  UNIQUE(dataset_id, version)
);

CREATE TABLE IF NOT EXISTS entities (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL, -- geo | company | index | sector
  code TEXT NOT NULL,
  name TEXT,
  country TEXT
);

CREATE TABLE IF NOT EXISTS indicators (
  id TEXT PRIMARY KEY,
  code TEXT NOT NULL,
  name TEXT,
  default_unit TEXT
);

CREATE TABLE IF NOT EXISTS observations_raw (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dataset_version_id INTEGER NOT NULL REFERENCES dataset_versions(id),
  entity_id TEXT,
  indicator_id TEXT,
  reference_period TEXT NOT NULL,
  frequency TEXT NOT NULL,
  value REAL NOT NULL,
  unit TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  payload_hash TEXT,
  UNIQUE(dataset_version_id, entity_id, indicator_id, reference_period, unit)
);

CREATE TABLE IF NOT EXISTS observations_normalized (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  raw_id INTEGER NOT NULL REFERENCES observations_raw(id),
  value REAL NOT NULL,
  unit TEXT NOT NULL,
  unit_dim TEXT NOT NULL,
  frequency TEXT NOT NULL,
  reference_period TEXT NOT NULL,
  period_kind TEXT NOT NULL -- flow | stock
);

CREATE TABLE IF NOT EXISTS gold_prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  observation_date TEXT NOT NULL,
  period TEXT,
  frequency TEXT NOT NULL, -- D M Q A
  price_eur_per_troy_oz REAL NOT NULL,
  unit TEXT NOT NULL DEFAULT 'EUR/troy_oz_Au999.9',
  methodology TEXT,
  retrieved_at TEXT NOT NULL,
  UNIQUE(source, observation_date, frequency)
);

CREATE TABLE IF NOT EXISTS au_observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  normalized_id INTEGER NOT NULL REFERENCES observations_normalized(id),
  derived_value REAL NOT NULL,
  derived_unit TEXT NOT NULL,
  gold_price REAL NOT NULL,
  gold_price_date_or_period TEXT NOT NULL,
  gold_alignment_method TEXT NOT NULL,
  gold_source TEXT NOT NULL,
  au_definition_version TEXT NOT NULL,
  transformation_formula TEXT NOT NULL,
  transformation_version TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  UNIQUE(normalized_id, transformation_version)
);

CREATE TABLE IF NOT EXISTS indices (
  id TEXT PRIMARY KEY,
  code TEXT NOT NULL,
  name TEXT,
  universe TEXT
);

CREATE TABLE IF NOT EXISTS companies (
  id TEXT PRIMARY KEY,
  name TEXT,
  country TEXT,
  isin TEXT
);

CREATE TABLE IF NOT EXISTS index_constituents (
  index_id TEXT NOT NULL REFERENCES indices(id),
  company_id TEXT NOT NULL REFERENCES companies(id),
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  weight REAL,
  classification TEXT,
  PRIMARY KEY(index_id, company_id, valid_from)
);

CREATE TABLE IF NOT EXISTS company_prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_id TEXT NOT NULL REFERENCES companies(id),
  observation_date TEXT NOT NULL,
  price_eur REAL,
  dividend_eur REAL,
  UNIQUE(company_id, observation_date)
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
  run_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  datasets_checked INTEGER DEFAULT 0,
  datasets_updated INTEGER DEFAULT 0,
  observations_added INTEGER DEFAULT 0,
  observations_updated INTEGER DEFAULT 0,
  observations_revised INTEGER DEFAULT 0,
  observations_rejected INTEGER DEFAULT 0,
  validation_errors TEXT,
  validation_warnings TEXT
);

CREATE TABLE IF NOT EXISTS validation_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT REFERENCES ingestion_runs(run_id),
  kind TEXT NOT NULL,
  ok INTEGER NOT NULL,
  detail TEXT
);

INSERT OR IGNORE INTO sources(id,name,kind,homepage,license_note) VALUES
 ('eurostat','Eurostat','eurostat','https://ec.europa.eu/eurostat','Eurostat reuse policy'),
 ('stoxx','STOXX','stoxx','https://www.stoxx.com','Licensed vendor — connector only publishes if licence permits'),
 ('gold','Gold EUR/oz','gold','https://data.ecb.europa.eu','ECB SDW XAU/EUR where available');
