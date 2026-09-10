"""€Au per inhabitant from Eurostat demo_pjan."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.request import Request, urlopen

POP_FILE = Path(__file__).resolve().parents[1] / "data" / "seed" / "population_demo_pjan.json"
GEO_ALIAS = {"GR": "EL", "UK": "GB"}


def load_pop() -> dict:
    if POP_FILE.is_file():
        return json.loads(POP_FILE.read_text())
    return {}


def nearest(pop: dict, geo: str, year: str):
    geo = GEO_ALIAS.get(geo, geo)
    d = pop.get(geo) or {}
    if year in d:
        return d[year]
    years = [y for y in d if str(y).isdigit()]
    if not years or not str(year).isdigit():
        return None
    return d[min(years, key=lambda y: abs(int(y) - int(year)))]


def unit_scale(unit: str) -> float:
    u = (unit or "").lower()
    if "million" in u or u.startswith("mio"):
        return 1e6
    if "milliard" in u:
        return 1e9
    return 1.0


def apply(observations: dict, pop: dict | None = None) -> int:
    pop = pop or load_pop()
    n = 0
    for key, rows in observations.items():
        parts = str(key).split("|")
        geo = (parts[1] if len(parts) > 1 else "").replace("geo:", "")
        for o in rows:
            year = str(o.get("period") or "")[:4]
            p = nearest(pop, geo, year)
            src, gold = o.get("source_value"), o.get("gold_price")
            if src is None or not gold or not p:
                o["au_per_capita"] = None
                o["population"] = p
                continue
            total_au = float(src) * unit_scale(o.get("source_unit")) * 100.0 / float(gold)
            o["population"] = p
            o["au_total"] = total_au
            o["au_per_capita"] = total_au / float(p)
            o["au_unit"] = "€Au per inhabitant"
            n += 1
    return n
