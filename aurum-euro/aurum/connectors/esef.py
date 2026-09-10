"""ESEF packages from filings.xbrl.org — current and historical.

Official reports of issuers on EU regulated markets. Not exchange prices.
Published unit after transform is €Au.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from .base import SourceConnector

API = "https://filings.xbrl.org/api/filings"
HOST = "https://filings.xbrl.org"
EURO_AREA = [
    "AT", "BE", "CY", "EE", "ES", "FI", "FR", "GR", "HR",
    "IT", "LT", "LU", "LV", "MT", "NL", "PT", "SI", "SK",
]
# DE and IE are absent from this aggregator at present.
WANT = {
    "Equity",
    "Assets",
    "Revenue",
    "EquityAttributableToOwnersOfParent",
    "ProfitLoss",
}


def _get_json(url: str, accept: str = "application/vnd.api+json", timeout: int = 40) -> dict:
    req = Request(url, headers={
        "User-Agent": "aurum-euro-refresh/1.0 (+https://eni.calhegasmorais.pt/aurum-euro)",
        "Accept": accept,
    })
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


class EsefConnector(SourceConnector):
    name = "esef"

    def discover(self) -> list[dict]:
        return [{"geo": c, "source": "filings.xbrl.org"} for c in EURO_AREA]

    def fetch(self, dataset_id: str = "index") -> dict:
        if dataset_id == "index":
            return {"filings": self.index()}
        return {"observations": []}

    def index(self, page_size: int = 100) -> list[dict]:
        rows, seen = [], set()
        for geo in EURO_AREA:
            for sort in ("-period_end", "period_end"):
                url = f"{API}?page[size]={page_size}&filter[country]={geo}&sort={sort}"
                try:
                    data = _get_json(url)
                except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
                    continue
                for item in data.get("data") or []:
                    a = item.get("attributes") or {}
                    lei = (a.get("viewer_url") or "").strip("/").split("/")[0]
                    period = a.get("period_end") or ""
                    year = period[:4]
                    if not lei or not year.isdigit() or not (2018 <= int(year) <= 2027):
                        continue
                    key = (lei, period)
                    if key in seen:
                        continue
                    seen.add(key)
                    j = a.get("json_url") or ""
                    rows.append({
                        "lei": lei,
                        "geo": geo,
                        "period": period,
                        "json_url": HOST + j if j.startswith("/") else j,
                    })
        return rows

    def extract_facts(self, json_url: str) -> dict:
        data = _get_json(json_url, accept="application/json", timeout=18)
        found: dict[str, float] = {}
        for fact in (data.get("facts") or {}).values():
            if not isinstance(fact, dict):
                continue
            dims = fact.get("dimensions") or {}
            name = str(dims.get("concept") or "").split(":")[-1]
            if name not in WANT:
                continue
            if str(dims.get("unit") or "") not in ("iso4217:EUR", "EUR"):
                continue
            try:
                num = float(str(fact.get("value")).replace(",", ""))
            except (TypeError, ValueError):
                continue
            if name not in found or abs(num) > abs(found[name]):
                found[name] = num
        return found
