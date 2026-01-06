from pathlib import Path
import json
from typing import Any, Dict, Optional


class StaticDataStore:
    """Loads static JSON data at startup and exposes read-only views."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self._cache: Dict[str, Any] = {}

    def load_all(self) -> None:
        self._cache["transit_metadata"] = self._load_json("data/transit_metadata.json")
        self._cache["tourist_places"] = self._load_json("data/tourist_places.json")
        self._cache["fares"] = self._load_json("data/fares.json")
        self._cache["transit_lines"] = self._load_json("data/transit_lines.json")

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def _load_json(self, relative: str) -> Any:
        path = self.base_path / relative
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
