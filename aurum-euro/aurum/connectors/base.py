from __future__ import annotations
from abc import ABC, abstractmethod

class SourceConnector(ABC):
    name: str

    @abstractmethod
    def discover(self) -> list[dict]: ...
    @abstractmethod
    def fetch(self, dataset_id: str) -> dict: ...
    def validate(self, payload: dict) -> list[str]:
        return []
    def normalize(self, payload: dict) -> list[dict]:
        return payload.get("observations") or []
    def publish(self, rows: list[dict]) -> int:
        return len(rows)
