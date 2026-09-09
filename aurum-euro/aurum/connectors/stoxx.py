"""STOXX connector. Historical constituents are point-in-time. Licence-gated fetch."""
from __future__ import annotations
from .base import SourceConnector

class StoxxConnector(SourceConnector):
    name = "stoxx"

    def discover(self) -> list[dict]:
        return [
            {"id": "SXXP", "title": "STOXX Europe 600", "kind": "index"},
            {"id": "SX5E", "title": "EURO STOXX 50", "kind": "index"},
        ]

    def fetch(self, dataset_id: str) -> dict:
        return {
            "dataset": dataset_id,
            "status": "licence_required",
            "note": "Do not scrape STOXX. Publish only with a licence. Schema (indices, constituents valid_from/to, weights) is ready.",
            "observations": [],
        }
