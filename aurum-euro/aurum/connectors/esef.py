"""ESEF packages from filings.xbrl.org — current and historical.

Official reports of issuers on EU regulated markets. Not exchange prices.
Published unit after transform is €Au.
"""
from __future__ import annotations
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from .base import SourceConnector

API = "https://filings.xbrl.org/api/filings"
HOST = "https://filings.xbrl.org"
EURO_AREA = [
    "AT", "BE", "CY", "DE", "EE", "ES", "FI", "FR", "GR", "HR",
    "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PT", "SI", "SK",
]
WANT = {
    "Equity",
    "Assets",
    "Revenue",
    "EquityAttributableToOwnersOfParent",
    "ProfitLoss",
}


def _get_json(url: str, accept: str = "application/vnd.api+json", timeout: int = 40) -> dict:
    req = Request(url, headers={
        "User-Agent": "aurum-euro-refresh/1.2 (+https://eni.calhegasmorais.pt/aurum-euro)",
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

    def index(self, page_size: int = 500, max_pages: int = 60) -> list[dict]:
        """Paginate the public catalogue and keep euro-area issuers only.

        filter[country] on this API now returns empty; country is applied here.
        """
        rows, seen = [], set()
        allowed = set(EURO_AREA)
        for page in range(1, max_pages + 1):
            url = f"{API}?page[size]={page_size}&page[number]={page}&sort=-period_end"
            try:
                data = _get_json(url)
            except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
                break
            items = data.get("data") or []
            if not items:
                break
            for item in items:
                a = item.get("attributes") or {}
                geo = (a.get("country") or "").upper()
                if geo not in allowed:
                    continue
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
        data = _get_json(json_url, accept="application/json", timeout=12)
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
