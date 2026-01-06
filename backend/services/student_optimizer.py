from typing import Dict, Any
from services.transit_lookup import find_transit_line, suggest_multimodal_route, get_surge_multiplier
from services.ride_pricing import get_estimated_ride_prices


def compute_options(home: str, destination: str, city: str, fares: Dict[str, Any], distance_km: float = 5.0, duration_min: float = 10.0, transit_lines: Dict[str, Any] = None, budget_limit: int = None) -> Dict[str, Any]:
    """Returns cheapest vs fastest using fare table and live/fallback distance/time."""
    city_fares = fares.get("cities", {}).get(city, {})
    surge = get_surge_multiplier()
    
    # Try to find actual transit line
    transit_line = None
    if transit_lines:
        transit_line = find_transit_line(home, destination, city, transit_lines)
        if not transit_line:
            transit_line = suggest_multimodal_route(home, destination, city, transit_lines, distance_km)
    
    city_fares = fares.get("cities", {}).get(city, {})
    bus_cost = city_fares.get("bus_flat", 20)
    metro_per_km = city_fares.get("metro_per_km", 4.0)
    auto_base = city_fares.get("auto_base", 35)
    auto_per_km = city_fares.get("auto_per_km", 18)

    if transit_line and transit_line['type'] == 'bus':
        cheapest_route = transit_line['line']
    else:
        cheapest_route = "Bus 215 (placeholder)"
    
    cheapest = {
        "mode": "Bus",
        "route": cheapest_route,
        "cost": f"₹{bus_cost}",
        "time": f"{int(max(duration_min * 1.1, distance_km * 9))} mins"
    }
    
    fastest_route = transit_line['line'] if transit_line and transit_line['type'] in ['metro', 'suburban_rail'] else "Metro + Auto"
    fastest_cost = int((auto_base + int(distance_km * metro_per_km)) * surge)
    fastest_time = int(max(duration_min * 0.8, distance_km * 6))
    fastest = {
        "mode": "Metro + Auto" if not transit_line else transit_line['type'].replace('_', ' ').title(),
        "route": fastest_route,
        "cost": f"₹{fastest_cost}{' (surge)' if surge > 1 else ''}",
        "time": f"{fastest_time} mins"
    }
    auto_cost = int((auto_base + int(distance_km * auto_per_km)) * surge)
    fallback_auto = {
        "mode": "Auto",
        "route": "Point-to-point",
        "cost": f"₹{auto_cost}{' (surge)' if surge > 1 else ''}",
        "time": f"{int(max(duration_min * 0.7, distance_km * 5))} mins"
    }
    
    # Get enhanced ride-hailing price estimates
    ride_estimates = get_estimated_ride_prices(
        origin=home,
        destination=destination,
        distance_km=distance_km,
        surge_multiplier=surge,
        user_type="student",
        budget_limit=budget_limit
    )
    
    return {
        "cheapest": cheapest,
        "fastest": fastest,
        "door_to_door": fallback_auto,
        "ride_options": ride_estimates["ride_options"],
        "ride_recommendation": ride_estimates["recommendation"],
        "distance_km": distance_km,
        "duration_min": duration_min,
        "surge_active": ride_estimates["surge_active"]
    }
