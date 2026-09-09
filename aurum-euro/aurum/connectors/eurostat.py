"""Eurostat official SDMX 2.1 TSV + Statistics JSON. No webpage scrape."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from .base import SourceConnector

SDMX = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
STAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
REG = Path(__file__).resolve().parents[2] / "data" / "seed" / "phase2_registry.json"


def _get(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "aurum-euro-repo/2.0 (+eni.calhegasmorais.pt/aurum-euro)"})
    with urlopen(req, timeout=90) as r:
        return r.read()


def parse_tsv(text: str) -> list[dict]:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0]
    left, times = header.split("\\TIME_PERIOD", 1)
    dim_names = [x.strip() for x in left.split(",")]
    periods = [p.strip() for p in times.split("\t") if p.strip() or True]
    # times string starts with tab-separated years; first token may be empty
    period_labels = [p.strip() for p in times.split("\t")]
    if period_labels and period_labels[0] == "":
        period_labels = period_labels[1:]
    rows = []
    for ln in lines[1:]:
        parts = ln.split("\t")
        keys = parts[0].split(",")
        vals = parts[1:]
        dims = dict(zip(dim_names, keys))
        for per, raw in zip(period_labels, vals):
            raw = (raw or "").strip()
            if raw in ("", ":", ": ", ":z", ":u", ":c"):
                continue
            flag = ""
            token = raw.split()[0] if raw else ""
            try:
                value = float(token.replace(",", ""))
            except ValueError:
                continue
            rows.append({
                "dims": dims,
                "period": per.strip(),
                "value": value,
                "flag": flag,
            })
    return rows


class EurostatConnector(SourceConnector):
    name = "eurostat"

    def discover(self) -> list[dict]:
        if REG.is_file():
            return json.loads(REG.read_text(encoding="utf-8")).get("series") or []
        return []

    def fetch_series(self, dataset: str, key: str) -> dict:
        url = f"{SDMX}{dataset}/{key}?format=TSV&compressed=false"
        raw = _get(url)
        dest = Path(__file__).resolve().parents[2] / "data" / "raw" / "eurostat" / dataset
        dest.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (dest / f"{key.replace('.','_')}_{stamp}.tsv").write_bytes(raw)
        text = raw.decode("utf-8", "replace")
        return {
            "dataset": dataset,
            "key": key,
            "url": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "observations": parse_tsv(text),
        }

    def fetch(self, dataset_id: str, **params) -> dict:
        # legacy JSON path
        from urllib.parse import urlencode
        url = STAT + dataset_id + "?" + urlencode({"format": "JSON", **params})
        raw = _get(url)
        return json.loads(raw.decode("utf-8"))
