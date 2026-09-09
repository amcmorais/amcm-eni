# Aurum Euro (€Au) — public data repository

Production path: https://eni.calhegasmorais.pt/aurum-euro

Primary product: automated acquisition, preservation, transformation and publication of Eurostat and STOXX data as historically aligned €Au series.

Covenant + Deflator Thesis are secondary. They do not drive the transform.

## Definition (immutable)

    100 €Au = 1 troy oz Au 999.9
    1 €Au   = 0.01 troy oz = 0.311034768 g Au 999.9

Wiener Philharmoniker 1 oz (Austrian Mint). The EUR gold price never redefines €Au.

## Transform

    X_au,t = X_eur,t * 100 / P_au_eur,t

Source rows stay. €Au rows are derived and provenanced.

## Phase 1

    cd aurum-euro
    PYTHONPATH=. python3 -m aurum.cli rebuild
    PYTHONPATH=. python3 -m aurum.cli serve --port 8091

- GET /api/v1/definition
- GET /api/v1/gold
- GET /api/v1/au/nama_10_gdp
- browser /

STOXX fetch is licence-gated; constituent `valid_from`/`valid_to` is in sql/schema.sql.

## Laws

1. Source data is sacred.
2. Same inputs → same €Au.
3. Gold alignment is explicit.
4. Units are dimensional.
5. The engine does not encode the Deflator Thesis.
