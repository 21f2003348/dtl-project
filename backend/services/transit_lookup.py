from typing import Dict, Any, List, Optional
from datetime import datetime


def is_peak_hour() -> bool:
    """Check if current time is peak hour (7-10 AM, 5-8 PM on weekdays)"""
    now = datetime.now()
    hour = now.hour
    is_weekday = now.weekday() < 5
    return is_weekday and ((7 <= hour < 10) or (17 <= hour < 20))


def get_surge_multiplier() -> float:
    """Return surge multiplier based on peak hours"""
    return 1.5 if is_peak_hour() else 1.0


def find_transit_line(origin: str, destination: str, city: str, transit_lines: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find best transit line connecting origin and destination."""
    city_data = transit_lines.get("cities", {}).get(city, {})
    
    def fuzzy_match(query: str, stations: List[str]) -> bool:
        """Check if query fuzzy-matches any station (partial match)"""
        query_lower = query.lower()
        return any(query_lower in station.lower() or station.lower() in query_lower for station in stations)
    
    def route_contains(route_text: str, location: str) -> bool:
        """Check if a route text contains a location (flexible matching)"""
        route_lower = route_text.lower()
        loc_lower = location.lower()
        # Direct match
        if loc_lower in route_lower:
            return True
        # Handle abbreviations and synonyms
        abbreviations = {
            "rvce": ["rv college", "rv", "rashtreeya vidyalaya"],
            "bsk": ["banashankari"],
            "jp nagar": ["jpn", "jp"],
            "btm": ["btm layout"],
            "mg road": ["mg", "mahatma gandhi road"],
            "majestic": ["kempegowda", "kbs", "kempegowda bus station"],
            "kempegowda bus station": ["majestic", "kbs"],
            "hebbal": ["mekhri circle", "esteem mall"]
        }
        for abbr, expansions in abbreviations.items():
            if loc_lower == abbr and any(exp in route_lower for exp in expansions):
                return True
            if any(exp == loc_lower for exp in expansions) and abbr in route_lower:
                return True
        return False
    
    # Check suburban rail first (Mumbai) - highest priority for long distances
    if "suburban_rail" in city_data:
        for line in city_data["suburban_rail"]["lines"]:
            stations = line["major_stations"]
            if fuzzy_match(origin, stations) and fuzzy_match(destination, stations):
                return {"type": "suburban_rail", "line": line["name"], "route": line["route"], "frequency": "5-10 mins (peak), 10-20 mins (off-peak)"}
    
    # Check metro lines - good for medium distances
    if "metro" in city_data:
        for line in city_data["metro"]["lines"]:
            stations = line["stations"]
            if fuzzy_match(origin, stations) and fuzzy_match(destination, stations):
                frequency = line.get("frequency", "10-15 mins")
                return {"type": "metro", "line": line["name"], "route": line["route"], "frequency": frequency}
    
    # Check bus routes with improved matching
    if "bus" in city_data and "major_routes" in city_data["bus"]:
        for route in city_data["bus"]["major_routes"]:
            route_text = route["route"]
            # Only return routes that cover BOTH origin and destination
            if route_contains(route_text, origin) and route_contains(route_text, destination):
                return {"type": "bus", "line": f"Bus {route['number']}", "route": route["route"], "frequency": route.get("frequency", "20-30 mins")}
    
    # No direct line found - don't return partial matches
    return None


def suggest_multimodal_route(origin: str, destination: str, city: str, transit_lines: Dict[str, Any], distance_km: float) -> Dict[str, Any]:
    """Suggest multi-modal route when no direct transit line exists."""
    # For very long distances (>25km) without direct transit, suggest auto to hub
    if distance_km > 25:
        hubs = {"Bengaluru": ["Majestic", "KR Puram", "Silk Board"], "Mumbai": ["Dadar", "Kurla", "Andheri"]}
        nearest_hub = hubs.get(city, ["City Center"])[0]
        return {
            "type": "multimodal",
            "line": f"Auto/Bus to {nearest_hub} + Metro/Bus",
            "route": f"{origin} → {nearest_hub} (feeder) → {destination} (transit)",
            "frequency": "Variable",
            "note": "Long distance - recommend auto/bus to nearest metro hub"
        }
    else:
        # Medium distance: suggest local bus or multiple bus connections
        return {
            "type": "bus",
            "line": "Local Bus (check BMTC/BEST app for routes)",
            "route": f"{origin} → {destination}",
            "frequency": "15-30 mins",
            "note": "Multiple bus routes available - check real-time app for best option"
        }
