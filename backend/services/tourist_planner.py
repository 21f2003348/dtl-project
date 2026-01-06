from typing import Dict, Any, List


def draft_itinerary(city: str, dataset: Dict[str, Any], days: int = 1) -> List[Dict[str, Any]]:
    """Creates a short, validated itinerary using curated places only."""
    city_data = dataset.get("cities", {}).get(city, {})
    safe_places = city_data.get("safe_places", [])
    days = max(1, min(days, 5))  # cap to keep deterministic
    itinerary: List[Dict[str, Any]] = []
    for idx in range(days):
        start = (idx * 2) % len(safe_places) if safe_places else 0
        stops = [p["name"] for p in safe_places[start:start + 2]] if safe_places else []
        itinerary.append({"day": idx + 1, "focus": city_data.get("themes", ["general"])[0], "stops": stops})
    return itinerary


def validate_itinerary(itinerary: List[Dict[str, str]], dataset: Dict[str, Any]) -> bool:
    """Ensures all suggested stops exist in curated list."""
    allowed = set()
    for city_obj in dataset.get("cities", {}).values():
        for place in city_obj.get("safe_places", []):
            allowed.add(place["name"])
    for day in itinerary:
        for stop in day.get("stops", []):
            if stop not in allowed:
                return False
    return True
