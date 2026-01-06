from typing import Dict, Any
from services.transit_lookup import find_transit_line, suggest_multimodal_route, is_peak_hour, get_surge_multiplier
from services.ride_pricing import get_estimated_ride_prices


def plan_safe_route(current_location: str, destination: str, city: str, transit_metadata: Dict[str, Any], distance_km: float = 5.0, duration_min: float = 10.0, transit_lines: Dict[str, Any] = None) -> Dict[str, Any]:
    """Prefers accessible, simple routes for elderly users."""
    cities = transit_metadata.get("cities", []) if isinstance(transit_metadata, dict) else []
    city_meta = next((c for c in cities if c.get("city") == city), {})
    metro_accessible = city_meta.get("accessibility", {}).get("metro") is True
    
    # Try to find actual transit line
    transit_line = None
    if transit_lines:
        print(f"[DEBUG elderly] Calling find_transit_line: origin={current_location}, dest={destination}, city={city}, has_data={bool(transit_lines)}")
        transit_line = find_transit_line(current_location, destination, city, transit_lines)
        print(f"[DEBUG elderly] Transit line result: {transit_line}")
        
        # If no direct line, suggest multimodal
        if not transit_line:
            transit_line = suggest_multimodal_route(current_location, destination, city, transit_lines, distance_km)
            print(f"[DEBUG elderly] Multimodal fallback: {transit_line}")
    
    if transit_line:
        freq_note = f" (every {transit_line.get('frequency', 'varies')})"
        route = f"{transit_line['line']} ({transit_line['type'].replace('_', ' ').title()}){freq_note}"
        explanation = transit_line.get('note', f"Found direct {transit_line['type'].replace('_', ' ')} line with good accessibility")
    elif metro_accessible:
        route = "Metro -> Walk"
        explanation = "Picked metro for better accessibility and predictable stops"
    else:
        route = "Bus -> Walk"
        explanation = "Metro not marked accessible; chose simple bus route"

    est_time = f"{int(duration_min * 1.2)} mins"  # Add 20% buffer for elderly pace
    est_cost = 30 if distance_km < 10 else min(50, int(distance_km * 2))  # Scale with distance
    
    # Get enhanced ride-hailing price estimates (elderly-friendly, no bikes)
    surge = get_surge_multiplier()
    ride_estimates = get_estimated_ride_prices(
        origin=current_location,
        destination=destination,
        distance_km=distance_km,
        surge_multiplier=surge,
        user_type="elderly",
        budget_limit=None  # No budget limit for elderly (prioritize comfort)
    )
    
    return {
        "mode": "elderly",
        "decision": "Simplest accessible route",
        "route": route,
        "cost": f"Est. ₹{est_cost}",
        "time": est_time,
        "explanation": explanation,
        "distance_km": distance_km,
        "duration_min": duration_min,
        "ride_options": ride_estimates["ride_options"],
        "ride_recommendation": ride_estimates["recommendation"],
        "safety_note": "Consider booking a cab if unfamiliar with public transit"
    }
