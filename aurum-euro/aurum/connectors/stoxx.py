
from __future__ import annotations
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from .base import SourceConnector

OFFICIAL = {
    "SX5E": "https://www.stoxx.com/documents/stoxxnet/Documents/Indices/Current/HistoricalData/h_sx5e.txt",
    "SXXP": "https://www.stoxx.com/documents/stoxxnet/Documents/Indices/Current/HistoricalData/h_sxxp.txt",
}

class StoxxConnector(SourceConnector):
    name = "stoxx"

    def discover(self):
        return [{"id": k, "title": k, "official_url": v} for k,v in OFFICIAL.items()]

    def fetch(self, dataset_id: str):
        url = OFFICIAL.get(dataset_id.upper()) or OFFICIAL["SXXP"]
        try:
            req = Request(url, headers={"User-Agent": "aurum-euro-repo/2.0"})
            with urlopen(req, timeout=30) as r:
                raw = r.read()
            return {"dataset": dataset_id, "status": "ok", "bytes": len(raw), "url": url}
        except HTTPError as e:
            return {
                "dataset": dataset_id,
                "status": "licence_required",
                "http": e.code,
                "url": url,
                "note": "STOXX official HistoricalData is 403 without a customer licence. Schema ready. Do not scrape.",
                "observations": [],
            }
