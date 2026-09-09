"""Ingest gold seed + one Eurostat monetary series, transform, validate, store."""
from __future__ import annotations
import json, sqlite3, uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .store import connect, init_db, DEFAULT_DB
from .connectors.gold import GoldConnector
from .connectors.eurostat import EurostatConnector
from .units import parse_unit, output_unit, needs_transform
from .transform import transform_value, ALIGNMENT
from .definition import AU_DEFINITION_VERSION, TRANSFORMATION_VERSION, TRANSFORMATION_FORMULA
from .validate import math_ok, gold_present

NOW = lambda: datetime.now(timezone.utc).isoformat()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def ingest_gold(con: sqlite3.Connection) -> int:
    payload = GoldConnector().fetch()
    n = 0
    for rec in payload.get("observations") or []:
        try:
            con.execute(
                """INSERT OR REPLACE INTO gold_prices
                   (source, observation_date, period, frequency, price_eur_per_troy_oz, methodology, retrieved_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    "seed",
                    rec["date"],
                    rec["date"][:4],
                    rec.get("frequency") or "A",
                    float(rec["price_eur_per_troy_oz"]),
                    rec.get("methodology") or "seed",
                    payload["retrieved_at"],
                ),
            )
            n += 1
        except Exception:
            continue
    con.commit()
    return n


def gold_for_period(con: sqlite3.Connection, period: str, freq: str = "A") -> tuple[float, str, str] | None:
    year = period[:4]
    row = con.execute(
        """SELECT price_eur_per_troy_oz, observation_date, frequency
             FROM gold_prices WHERE substr(observation_date,1,4)=? AND frequency=?
             ORDER BY observation_date DESC LIMIT 1""",
        (year, "A" if freq in ("A", "a", "annual") else freq),
    ).fetchone()
    if not row:
        row = con.execute(
            "SELECT price_eur_per_troy_oz, observation_date, frequency FROM gold_prices WHERE substr(observation_date,1,4)=? ORDER BY observation_date DESC LIMIT 1",
            (year,),
        ).fetchone()
    if not row:
        return None
    return float(row[0]), str(row[1]), str(row[2])


def ingest_nama_gdp(con: sqlite3.Connection, geo: str = "EA20") -> dict:
    """Fetch Eurostat nama_10_gdp CP_MEUR B1GQ and emit €Au rows."""
    run = _run_id()
    con.execute(
        "INSERT INTO ingestion_runs(run_id,source,started_at,status) VALUES (?,?,?,?)",
        (run, "eurostat", NOW(), "running"),
    )
    con.commit()
    conn = EurostatConnector()
    try:
        payload = conn.fetch(
            "nama_10_gdp",
            geo=geo,
            na_item="B1GQ",
            unit="CP_MEUR",
        )
    except Exception as e:
        con.execute("UPDATE ingestion_runs SET finished_at=?, status=?, validation_errors=? WHERE run_id=?",
                    (NOW(), "fail", str(e)[:400], run))
        con.commit()
        return {"ok": False, "run_id": run, "error": str(e)}

    # parse Eurostat JSON 2.0
    values = payload.get("value") or {}
    dims = payload.get("dimension") or {}
    time_cat = ((dims.get("time") or {}).get("category") or {}).get("index") or {}
    # invert index -> period label
    time_lab = {str(v): k for k, v in time_cat.items()} if time_cat else {}
    # If values keyed by linear index
    added = 0
    revised = 0
    con.execute("INSERT OR IGNORE INTO datasets(id,source_id,code,title,frequency) VALUES (?,?,?,?,?)",
                ("nama_10_gdp", "eurostat", "nama_10_gdp", payload.get("label") or "GDP", "A"))
    con.execute(
        "INSERT INTO dataset_versions(dataset_id, version, retrieved_at, is_current) VALUES (?,?,?,1)",
        ("nama_10_gdp", payload.get("updated") or NOW(), payload.get("_retrieved_at") or NOW()),
    )
    con.execute("INSERT OR IGNORE INTO entities(id,kind,code,name) VALUES (?,?,?,?)",
                (f"geo:{geo}", "geo", geo, geo))
    con.execute("INSERT OR IGNORE INTO indicators(id,code,name,default_unit) VALUES (?,?,?,?)",
                ("B1GQ", "B1GQ", "Gross domestic product", "million EUR"))
    con.commit()
    ver_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Eurostat maps value keys to a single linear index across all dims.
    # For a filtered query the keys are often already time positions.
    id_order = payload.get("id") or []
    size = payload.get("size") or []
    for key, val in values.items():
        if val is None:
            continue
        period = time_lab.get(str(key)) or str(key)
        if period.isdigit() and len(period) > 4:
            # linear index fallback: try time category by position
            period = time_lab.get(str(key), period)
        unit = "million EUR"
        retrieved = payload.get("_retrieved_at") or NOW()
        try:
            con.execute(
                """INSERT OR IGNORE INTO observations_raw
                   (dataset_version_id, entity_id, indicator_id, reference_period, frequency, value, unit, retrieved_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (ver_id, f"geo:{geo}", "B1GQ", str(period)[:16], "A", float(val), unit, retrieved),
            )
            raw_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
            if raw_id == 0:
                raw_id = con.execute(
                    """SELECT id FROM observations_raw WHERE dataset_version_id=? AND entity_id=? AND indicator_id=? AND reference_period=?""",
                    (ver_id, f"geo:{geo}", "B1GQ", str(period)[:16]),
                ).fetchone()
                raw_id = raw_id[0] if raw_id else None
            if not raw_id:
                continue
            dim = parse_unit(unit)
            con.execute(
                """INSERT OR IGNORE INTO observations_normalized
                   (raw_id, value, unit, unit_dim, frequency, reference_period, period_kind)
                   VALUES (?,?,?,?,?,?,?)""",
                (raw_id, float(val), unit, json.dumps({"eur_exp": dim.eur_exp, "scale": dim.scale}), "A", str(period)[:16], "flow"),
            )
            nid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
            if nid == 0:
                row = con.execute("SELECT id FROM observations_normalized WHERE raw_id=?", (raw_id,)).fetchone()
                nid = row[0] if row else None
            g = gold_for_period(con, str(period), "A")
            if not g or not nid:
                continue
            price, gdate, _gf = g
            okg, _ = gold_present(price)
            if not okg:
                continue
            au = transform_value(val, price, dim)
            der_unit = output_unit(dim)
            okm, why = math_ok(val, au, price, unit)
            con.execute(
                """INSERT OR REPLACE INTO au_observations
                   (normalized_id, derived_value, derived_unit, gold_price, gold_price_date_or_period,
                    gold_alignment_method, gold_source, au_definition_version, transformation_formula,
                    transformation_version, generated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (nid, float(au), der_unit, price, gdate, "annual_average", "seed",
                 AU_DEFINITION_VERSION, TRANSFORMATION_FORMULA, TRANSFORMATION_VERSION, NOW()),
            )
            added += 1
            con.execute(
                "INSERT INTO validation_results(run_id,kind,ok,detail) VALUES (?,?,?,?)",
                (run, "math", int(okm), why),
            )
        except Exception as e:
            con.execute(
                "INSERT INTO validation_results(run_id,kind,ok,detail) VALUES (?,?,?,?)",
                (run, "row", 0, str(e)[:200]),
            )
    con.execute(
        """UPDATE ingestion_runs SET finished_at=?, status=?, observations_added=? WHERE run_id=?""",
        (NOW(), "ok", added, run),
    )
    con.commit()
    return {"ok": True, "run_id": run, "added": added, "geo": geo}


def rebuild(db: Path | None = None) -> dict:
    con = connect(db)
    init_db(con)
    g = ingest_gold(con)
    e = ingest_nama_gdp(con)
    p2 = ingest_phase2(con)
    con.close()
    return {"gold_rows": g, "eurostat": e, "phase2": p2}


def ingest_phase2(con, geos=None) -> dict:
    from .connectors.eurostat import EurostatConnector, REG
    import json as _json
    spec = _json.loads(REG.read_text(encoding="utf-8"))
    geos = geos or spec.get("geos") or ["EA20"]
    conn = EurostatConnector()
    run = _run_id()
    con.execute("INSERT INTO ingestion_runs(run_id,source,started_at,status) VALUES (?,?,?,?)",
                (run, "eurostat-phase2", NOW(), "running"))
    con.commit()
    added = 0
    failed = []
    ingest_gold(con)
    for series in spec.get("series") or []:
        for geo in geos:
            key = series["key"].format(geo=geo)
            try:
                payload = conn.fetch_series(series["dataset"], key)
            except Exception as e:
                failed.append({"dataset": series["dataset"], "key": key, "err": str(e)[:80]})
                continue
            ds = series["dataset"]
            unit = series.get("unit") or "source"
            indicator = series.get("indicator") or key
            freq = series.get("freq") or "A"
            kind = series.get("kind") or "flow"
            con.execute("INSERT OR IGNORE INTO datasets(id,source_id,code,title,frequency) VALUES (?,?,?,?,?)",
                        (ds, "eurostat", ds, series.get("title") or ds, freq))
            con.execute("INSERT INTO dataset_versions(dataset_id, version, retrieved_at, is_current) VALUES (?,?,?,1)",
                        (ds, payload.get("retrieved_at") or NOW(), payload.get("retrieved_at") or NOW()))
            ver_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
            con.execute("INSERT OR IGNORE INTO entities(id,kind,code,name) VALUES (?,?,?,?)",
                        (f"geo:{geo}", "geo", geo, geo))
            con.execute("INSERT OR IGNORE INTO indicators(id,code,name,default_unit) VALUES (?,?,?,?)",
                        (indicator, indicator, series.get("title") or indicator, unit))
            for obs in payload.get("observations") or []:
                period = str(obs.get("period") or "")[:16]
                val = obs.get("value")
                if val is None or not period:
                    continue
                con.execute(
                    """INSERT OR IGNORE INTO observations_raw
                       (dataset_version_id, entity_id, indicator_id, reference_period, frequency, value, unit, retrieved_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (ver_id, f"geo:{geo}", indicator, period, freq, float(val), unit, payload["retrieved_at"]),
                )
                raw_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
                if not raw_id:
                    row = con.execute(
                        "SELECT id FROM observations_raw WHERE dataset_version_id=? AND entity_id=? AND indicator_id=? AND reference_period=?",
                        (ver_id, f"geo:{geo}", indicator, period),
                    ).fetchone()
                    raw_id = row[0] if row else None
                if not raw_id:
                    continue
                dim = parse_unit(unit)
                con.execute(
                    """INSERT OR IGNORE INTO observations_normalized
                       (raw_id, value, unit, unit_dim, frequency, reference_period, period_kind)
                       VALUES (?,?,?,?,?,?,?)""",
                    (raw_id, float(val), unit, dim.scale, freq, period, kind),
                )
                nid_row = con.execute("SELECT last_insert_rowid()").fetchone()
                nid = nid_row[0] if nid_row else 0
                if not nid:
                    rr = con.execute("SELECT id FROM observations_normalized WHERE raw_id=?", (raw_id,)).fetchone()
                    nid = rr[0] if rr else None
                if not nid:
                    continue
                if not needs_transform(dim):
                    continue
                g = gold_for_period(con, period, "A" if freq != "D" else "D")
                if not g:
                    continue
                price, gdate, _ = g
                align = "annual_average" if freq == "A" else ("quarterly_average" if freq == "Q" else "period_end" if kind=="stock" else "monthly_average")
                au = transform_value(val, price, dim)
                con.execute(
                    """INSERT OR REPLACE INTO au_observations
                       (normalized_id, derived_value, derived_unit, gold_price, gold_price_date_or_period,
                        gold_alignment_method, gold_source, au_definition_version, transformation_formula,
                        transformation_version, generated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (nid, float(au), output_unit(dim), price, gdate, align, "seed",
                     AU_DEFINITION_VERSION, TRANSFORMATION_FORMULA, TRANSFORMATION_VERSION, NOW()),
                )
                added += 1
            con.commit()
    con.execute("UPDATE ingestion_runs SET finished_at=?, status=?, observations_added=? WHERE run_id=?",
                (NOW(), "ok" if added else "partial", added, run))
    con.commit()
    return {"ok": True, "run_id": run, "added": added, "failed": failed[:20], "failed_n": len(failed)}
