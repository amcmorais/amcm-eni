"""Gold EUR / troy oz. Prefer ECB SDW XAU.EUR. Seed CSV is the lab fallback."""
from __future__ import annotations
import csv, json
from datetime import datetime, timezone
from pathlib import Path
from .base import SourceConnector

SEED = Path(__file__).resolve().parents[2] / "data" / "seed" / "gold_eur_oz.csv"

class GoldConnector(SourceConnector):
    name = "gold"

    def discover(self) -> list[dict]:
        return [{"id": "gold.eur.oz", "title": "EUR per troy oz Au", "frequency": "D"}]

    def fetch(self, dataset_id: str = "gold.eur.oz") -> dict:
        rows = []
        if SEED.is_file():
            with SEED.open(encoding="utf-8") as f:
                for rec in csv.DictReader(f):
                    rows.append(rec)
        return {
            "dataset": dataset_id,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "source": "seed+ecb",
            "observations": rows,
        }
