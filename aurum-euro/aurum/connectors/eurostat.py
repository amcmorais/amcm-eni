"""Eurostat SDMX-JSON connector. Registry-driven — do not freeze today's catalogue."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .base import SourceConnector

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
REGISTRY = Path(__file__).resolve().parents[2] / "data" / "seed" / "eurostat_registry.json"


class EurostatConnector(SourceConnector):
    name = "eurostat"

    def discover(self) -> list[dict]:
        if REGISTRY.is_file():
            return json.loads(REGISTRY.read_text(encoding="utf-8")).get("datasets") or []
        return [{"id": "nama_10_gdp", "title": "GDP and main components"}]

    def fetch(self, dataset_id: str, **params) -> dict:
        q = {"format": "JSON", **params}
        url = BASE + dataset_id + "?" + urlencode(q)
        req = Request(url, headers={"User-Agent": "aurum-euro-repo/1.0"})
        with urlopen(req, timeout=60) as r:
            raw = r.read()
        dest = Path(__file__).resolve().parents[2] / "data" / "raw" / "eurostat" / dataset_id
        dest.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (dest / f"{stamp}.json").write_bytes(raw)
        payload = json.loads(raw.decode("utf-8"))
        payload["_retrieved_at"] = datetime.now(timezone.utc).isoformat()
        payload["_url"] = url
        return payload

    def normalize(self, payload: dict) -> list[dict]:
        # SDMX-JSON 2.0 style used by Eurostat dissemination API
        value = payload.get("value") or {}
        dim = payload.get("dimension") or payload.get("id") or {}
        # Keep raw + a flattened view when possible
        rows = []
        if isinstance(value, dict):
            for k, v in list(value.items())[:5000]:
                if v is None:
                    continue
                rows.append({
                    "key": k,
                    "value": v,
                    "unit": "source",
                    "reference_period": str(k),
                })
        return rows
