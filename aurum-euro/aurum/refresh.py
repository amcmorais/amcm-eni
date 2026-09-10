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
        "note": "Automated ESEF refresh. Unit €Au. Euro is provenance. Not prices. Not STOXX.",
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
