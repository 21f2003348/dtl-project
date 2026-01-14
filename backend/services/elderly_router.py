"""
Elderly Router - Comfort-focused route planning for senior citizens.
Ranks all route options by comfort, safety, and accessibility.
"""
from typing import Dict, Any, List, Optional
from services.transit_lookup import find_transit_line, suggest_multimodal_route, is_peak_hour, get_surge_multiplier
from services.ride_pricing import get_estimated_ride_prices


def calculate_comfort_score(option: Dict[str, Any]) -> int:
    """
    Calculate comfort score for a route option.
    Higher score = more comfortable for elderly users.
    
    Factors:
    - AC availability: +20 points
    - Guaranteed seating: +15 points
    - Minimal walking: +10 points per 100m less than 500m
    - Fewer transfers: +10 points per transfer avoided
    - Door-to-door: +25 points
    - Off-peak timing: +5 points
    """
    score = 0
    mode = option.get("mode", "").lower()
    
    # AC availability
    if mode in ["metro", "cab", "ola", "uber", "auto (ac)"]:
        score += 20
    elif mode == "auto":
        score += 5  # Some autos have AC
    
    # Guaranteed seating
    if mode in ["cab", "ola", "uber", "auto", "rapido"]:
        score += 15  # Private transport = guaranteed seat
    elif mode == "metro" and not is_peak_hour():
        score += 10  # Metro off-peak usually has seats
    
    # Door-to-door service
    if mode in ["cab", "ola", "uber", "auto", "rapido"]:
        score += 25
    
    # Walking distance penalty
    walking_m = option.get("walking_m", 300)
    if walking_m < 100:
        score += 20
    elif walking_m < 200:
        score += 15
    elif walking_m < 300:
        score += 10
    elif walking_m < 500:
        score += 5
    # More than 500m walking is uncomfortable for elderly
    
    # Transfer penalty
    transfers = option.get("transfers", 0)
    score += max(0, (3 - transfers) * 10)  # Max 30 points for no transfers
    
    # Off-peak bonus
    if not is_peak_hour():
        score += 5
    
    # Time penalty for very long journeys
    time_min = option.get("time", 30)
    if time_min > 60:
        score -= 10
    elif time_min > 45:
        score -= 5
    
    return max(0, score)  # Ensure non-negative


def _build_all_options(
    origin: str, 
    destination: str, 
    city: str,
    distance_km: float,
    duration_min: float,
    transit_lines: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """Build all available route options with comfort scores."""
    options = []
    surge = get_surge_multiplier()
    
    # Option 1: Metro (if available)
    transit_line = None
    if transit_lines:
        transit_line = find_transit_line(origin, destination, city, transit_lines)
    
    if transit_line and transit_line.get("type") == "metro":
        metro_time = int(duration_min * 0.7)  # Metro is usually faster
        options.append({
            "mode": "Metro",
            "line": transit_line.get("line", "Metro"),
            "route_info": transit_line.get("route", f"{origin} → {destination}"),
            "cost": min(60, max(15, int(distance_km * 4))),
            "time": metro_time + 10,  # Add walking time
            "walking_m": 400,  # Average walk to metro
            "transfers": transit_line.get("transfers", 0),
            "frequency": transit_line.get("frequency", "5-10 mins"),
            "ac": True,
            "steps": [
                f"🚶 Walk to {origin} Metro Station (~5 mins)",
                f"🚇 Take {transit_line.get('line', 'Metro')} towards {destination}",
                f"📍 Get off at {destination} station",
                f"🚶 Walk to your destination (~5 mins)"
            ]
        })
    
    # Option 2: Bus
    bus_line = None
    if transit_lines:
        bus_line = find_transit_line(origin, destination, city, transit_lines)
        if not bus_line or bus_line.get("type") != "bus":
            # Try to find a bus specifically
            city_data = transit_lines.get("cities", {}).get(city, {})
            if "bus" in city_data:
                for route in city_data["bus"].get("major_routes", []):
                    route_text = route["route"].lower()
                    if origin.lower() in route_text or destination.lower() in route_text:
                        bus_line = {
                            "type": "bus",
                            "line": f"Bus {route['number']}",
                            "route": route["route"],
                            "frequency": route.get("frequency", "20 mins")
                        }
                        break
    
    if bus_line and bus_line.get("type") == "bus":
        options.append({
            "mode": "Bus",
            "line": bus_line.get("line", "Local Bus"),
            "route_info": bus_line.get("route", f"{origin} → {destination}"),
            "cost": 25,  # Flat fare
            "time": int(duration_min * 1.5) + 10,  # Slower than driving
            "walking_m": 300,
            "transfers": 0,
            "frequency": bus_line.get("frequency", "15-20 mins"),
            "ac": False,
            "steps": [
                f"🚶 Walk to nearest bus stop (~3 mins)",
                f"🚌 Take {bus_line.get('line', 'Bus')} towards {destination}",
                f"📍 Get off near {destination}",
                f"🚶 Walk to your destination (~3 mins)"
            ]
        })
    
    # Option 3: Auto-rickshaw
    auto_base = 35
    auto_per_km = 18
    auto_cost = int((auto_base + distance_km * auto_per_km) * surge)
    auto_time = max(10, int(duration_min * 1.1))
    
    options.append({
        "mode": "Auto",
        "line": "Auto-rickshaw",
        "route_info": "Door-to-door service",
        "cost": auto_cost,
        "time": auto_time,
        "walking_m": 0,
        "transfers": 0,
        "ac": False,
        "door_to_door": True,
        "steps": [
            f"🛺 Book or hail an auto from {origin}",
            f"💰 Pay approximately ₹{auto_cost}",
            f"📍 Direct ride to {destination}"
        ]
    })
    
    # Option 4: Cab (Ola/Uber)
    cab_cost = int((50 + distance_km * 15) * surge)  # Higher base, lower per km
    cab_time = max(10, int(duration_min))
    
    options.append({
        "mode": "Cab",
        "line": "Ola/Uber",
        "route_info": "AC, Door-to-door service",
        "cost": cab_cost,
        "time": cab_time + 5,  # Add pickup wait time
        "walking_m": 0,
        "transfers": 0,
        "ac": True,
        "door_to_door": True,
        "steps": [
            f"📱 Book a cab on Ola/Uber app",
            f"⏰ Wait for pickup (~5 mins)",
            f"🚗 AC ride to {destination}",
            f"💰 Pay approximately ₹{cab_cost}"
        ]
    })
    
    # Calculate comfort score for each option
    for opt in options:
        opt["comfort_score"] = calculate_comfort_score(opt)
    
    return options


def plan_safe_route(
    current_location: str, 
    destination: str, 
    city: str, 
    transit_metadata: Dict[str, Any], 
    distance_km: float = 5.0, 
    duration_min: float = 10.0, 
    transit_lines: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Plan routes for elderly users with comfort-ranked options.
    
    Returns all available options ranked by comfort score,
    with the most comfortable and fastest options highlighted.
    """
    # Build all available options
    all_options = _build_all_options(
        current_location, destination, city,
        distance_km, duration_min, transit_lines
    )
    
    # Sort by comfort score (highest first), then by time
    ranked_options = sorted(
        all_options, 
        key=lambda x: (-x["comfort_score"], x["time"])
    )
    
    # Identify most comfortable and fastest
    most_comfortable = ranked_options[0] if ranked_options else None
    fastest = min(ranked_options, key=lambda x: x["time"]) if ranked_options else None
    
    # Get ride-hailing estimates
    surge = get_surge_multiplier()
    ride_estimates = get_estimated_ride_prices(
        origin=current_location,
        destination=destination,
        distance_km=distance_km,
        surge_multiplier=surge,
        user_type="elderly",
        budget_limit=None
    )
    
    # Build response explanation
    if most_comfortable:
        if most_comfortable["mode"] in ["Cab", "Auto"]:
            recommendation = f"We recommend a {most_comfortable['mode']} for maximum comfort and door-to-door service."
        else:
            recommendation = f"The most comfortable option is {most_comfortable['mode']} ({most_comfortable['line']})."
    else:
        recommendation = "Please consider booking a cab for the safest journey."
    
    return {
        "mode": "elderly",
        "decision": "Comfort-ranked route options",
        "most_comfortable": most_comfortable,
        "fastest": fastest,
        "all_options": ranked_options,
        "route": most_comfortable.get("line", "Cab recommended") if most_comfortable else "Cab recommended",
        "cost": f"₹{most_comfortable['cost']}" if most_comfortable else "₹100-200",
        "time": f"{most_comfortable['time']} mins" if most_comfortable else "20-30 mins",
        "explanation": recommendation,
        "distance_km": distance_km,
        "duration_min": duration_min,
        "ride_options": ride_estimates.get("ride_options", []),
        "ride_recommendation": ride_estimates.get("recommendation", ""),
        "safety_note": "For unfamiliar routes, we recommend booking a cab with the Ola/Uber app for door-to-door service."
    }
