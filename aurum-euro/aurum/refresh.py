"""Unattended refresh: official sources → €Au snapshot the site publishes."""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .connectors.esef import EsefConnector
from .connectors.gold import GoldConnector
from .definition import AU_DEFINITION_VERSION, TRANSFORMATION_FORMULA

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "stocks-snapshot.json"


def gold_by_year() -> dict[str, float]:
    payload = GoldConnector().fetch()
    out = {}
    for rec in payload.get("observations") or []:
        y = str(rec.get("date") or "")[:4]
        if y:
            out[y] = float(rec["price_eur_per_troy_oz"])
    return out


def to_au(eur: float, price: float) -> float:
    return eur * 100.0 / price


def select_extract_batch(filings: list[dict], per_geo: int = 5) -> list[dict]:
    by = defaultdict(list)
    for row in filings:
        by[row["geo"]].append(row)
    batch, seen = [], set()
    for items in by.values():
        items = sorted(items, key=lambda x: x["period"])
        for row in items[:2] + items[-per_geo:]:
            key = (row["lei"], row["period"])
            if key in seen:
                continue
            seen.add(key)
            batch.append(row)
    return batch


def refresh_stocks(per_geo: int = 5) -> dict:
    gold = gold_by_year()
    conn = EsefConnector()
    filings = conn.index()
    batch = select_extract_batch(filings, per_geo=per_geo)
    observations = []
    for row in batch:
        try:
            facts = conn.extract_facts(row["json_url"])
        except Exception:
            continue
        year = row["period"][:4]
        px = gold.get(year) or gold.get("2024")
        if not facts or not px:
            continue
        obs = {
            "lei": row["lei"],
            "geo": row["geo"],
            "period": row["period"],
            "source": "ESEF",
            "gold_eur_oz": px,
            "au_definition": AU_DEFINITION_VERSION,
            "formula": TRANSFORMATION_FORMULA,
        }
        if "Equity" in facts:
            obs["equity_au"] = round(to_au(facts["Equity"], px), 4)
            obs["equity_eur_source"] = facts["Equity"]
        elif "EquityAttributableToOwnersOfParent" in facts:
            obs["equity_au"] = round(to_au(facts["EquityAttributableToOwnersOfParent"], px), 4)
            obs["equity_eur_source"] = facts["EquityAttributableToOwnersOfParent"]
        if "Assets" in facts:
            obs["assets_au"] = round(to_au(facts["Assets"], px), 4)
        if "Revenue" in facts:
            obs["revenue_au"] = round(to_au(facts["Revenue"], px), 4)
        if any(k in obs for k in ("equity_au", "assets_au", "revenue_au")):
            observations.append(obs)

    issuers = {}
    for row in filings:
        cur = issuers.get(row["lei"])
        if not cur:
            issuers[row["lei"]] = {
                "lei": row["lei"], "geo": row["geo"],
                "period_from": row["period"], "period_to": row["period"], "filings": 1,
            }
        else:
            cur["period_from"] = min(cur["period_from"], row["period"])
            cur["period_to"] = max(cur["period_to"], row["period"])
            cur["filings"] += 1
    latest = {}
    for obs in observations:
        prev = latest.get(obs["lei"])
        if not prev or obs["period"] >= prev["period"]:
            latest[obs["lei"]] = obs
    issuer_rows = []
    for lei, meta in issuers.items():
        rec = dict(meta)
        rec["source"] = "ESEF"
        if lei in latest:
            L = latest[lei]
            for k in ("equity_au", "equity_eur_source", "assets_au", "revenue_au", "period"):
                if k in L:
                    rec[k] = L[k]
        issuer_rows.append(rec)

    pack = {
        "publication_unit": "€Au",
        "coverage": "current_and_historical",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_issuers": len(issuer_rows),
        "n_filings_indexed": len(filings),
        "n_eau_observations": len(observations),
        "eau_years": sorted({o["period"][:4] for o in observations}),
        "note": "Automated ESEF refresh. Unit €Au. Euro is provenance. Not prices. ",
        "issuers": issuer_rows,
        "observations": observations,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pack, separators=(",", ":")))
    return {
        "ok": True,
        "path": str(OUT),
        "n_issuers": pack["n_issuers"],
        "n_filings_indexed": pack["n_filings_indexed"],
        "n_eau_observations": pack["n_eau_observations"],
        "eau_years": pack["eau_years"],
        "generated_at": pack["generated_at"],
    }


def refresh_eurostat() -> dict:
    from .store import connect, init_db
    from .pipeline import ingest_gold, ingest_phase2, ingest_nama_gdp
    from .scale import RULE
    con = connect(); init_db(con)
    ingest_gold(con)
    try:
        p2 = ingest_phase2(con)
    except Exception as e:
        p2 = {"ok": False, "err": str(e)[:120]}
    try:
        n1 = ingest_nama_gdp(con)
    except Exception as e:
        n1 = {"ok": False, "err": str(e)[:120]}
    gold = [dict(r) for r in con.execute(
        "select observation_date, frequency, price_eur_per_troy_oz, methodology, source from gold_prices order by 1")]
    rows = []
    q = """
    SELECT v.dataset_id as dataset, r.entity_id, r.indicator_id, r.reference_period AS period,
           r.value AS source_value, r.unit AS source_unit,
           a.gold_price, a.gold_alignment_method,
           a.derived_value AS au_value, a.derived_unit AS au_unit
      FROM au_observations a
      JOIN observations_normalized n ON n.id=a.normalized_id
      JOIN observations_raw r ON r.id=n.raw_id
      JOIN dataset_versions v ON v.id=r.dataset_version_id
     ORDER BY v.dataset_id, r.entity_id, r.indicator_id, r.reference_period
    """
    obs = {}
    for r in con.execute(q):
        d = dict(r)
        key = f"{d['dataset']}|{d['entity_id']}|{d['indicator_id']}"
        obs.setdefault(key, []).append({
            "period": d["period"], "source_value": d["source_value"], "source_unit": d["source_unit"],
            "gold_price": d["gold_price"], "gold_alignment_method": d["gold_alignment_method"],
            "au_value": d["au_value"], "au_unit": "€Au per inhabitant",
        })
    from .percapita import apply as apply_per_capita
    apply_per_capita(obs)
    GEO = {
        "EA20":"Euro area","EU27_2020":"European Union",
        "AT":"Austria","BE":"Belgium","CY":"Cyprus","DE":"Germany","EE":"Estonia",
        "ES":"Spain","FI":"Finland","FR":"France","GR":"Greece","HR":"Croatia",
        "IE":"Ireland","IT":"Italy","LT":"Lithuania","LU":"Luxembourg","LV":"Latvia",
        "MT":"Malta","NL":"Netherlands","PT":"Portugal","SI":"Slovenia","SK":"Slovakia",
    }
    IND = {
        "B1GQ":"Gross domestic product","P3":"Final consumption",
        "P31_S14":"Household final consumption","P31_S13":"Government final consumption",
        "P51G":"Gross fixed capital formation","P52":"Changes in inventories",
        "P6":"Exports","P7":"Imports","B11":"External balance",
        "D1":"Compensation of employees","B2A3G":"Gross operating surplus",
        "B9":"Net lending or borrowing","TE":"Government expenditure","TR":"Government revenue",
    }
    DS = {
        "nama_10_gdp":"National accounts — GDP and main aggregates",
        "namq_10_gdp":"National accounts — quarterly GDP",
        "namq_10_fcs":"National accounts — quarterly consumption",
        "gov_10a_main":"Government main aggregates",
    }
    catalog = []
    for k in sorted(obs):
        parts = k.split("|")
        ds = parts[0] if parts else ""
        geo = (parts[1] if len(parts)>1 else "").replace("geo:","")
        ind = parts[2] if len(parts)>2 else ""
        catalog.append({
            "id": k,
            "dataset_id": ds,
            "dataset_title": DS.get(ds, ds),
            "geography_id": geo,
            "geography": GEO.get(geo, geo),
            "indicator_id": ind,
            "indicator": IND.get(ind, ind),
        })
    pack = {
        "publication_unit": "€Au",
        "scale": "long",
        "scale_rule": RULE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gold": gold,
        "observations": obs,
        "series": sorted(obs),
        "catalog": catalog,
        "status": {
            "gold_rows": len(gold),
            "au_observations": sum(len(v) for v in obs.values()),
            "source": "Eurostat SDMX automated refresh",
        },
        "definition": {
            "equation": "100 €Au = 1 troy oz Au 999.9",
            "formula": TRANSFORMATION_FORMULA,
        },
    }
    dest = ROOT / "web" / "accounts-snapshot.json"
    dest.write_text(json.dumps(pack, separators=(",", ":")))
    return {"ok": True, "path": str(dest), "au_observations": pack["status"]["au_observations"], "series": len(obs), "phase2": p2, "nama": n1}


def refresh_all() -> dict:
    euro = refresh_eurostat()
    stocks = refresh_stocks()
    return {"publication_unit": "€Au", "scale": "long", "eurostat": euro, "esef": stocks}
