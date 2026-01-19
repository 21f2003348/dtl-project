"""
Elderly Router - Comfort-focused route planning for senior citizens.
Ranks all route options by comfort, safety, and accessibility.
"""
from typing import Dict, Any, List, Optional
from services.transit_lookup import find_transit_line, suggest_multimodal_route, is_peak_hour, get_surge_multiplier
from services.ride_pricing import get_estimated_ride_prices

# Vehicle capacity limits
VEHICLE_CAPACITY = {
    "auto": 3,
    "sedan_cab": 4,
    "suv_cab": 6,
    "bus": 50,
    "metro": 200
}

def calculate_per_person_cost(total_cost: int, num_people: int, vehicle_capacity: int) -> Dict[str, Any]:
    """Calculate per-person cost respecting vehicle capacity."""
    if num_people <= vehicle_capacity:
        # Single vehicle
        per_person = total_cost / num_people
        return {
            "total_cost": total_cost,
            "per_person_cost": round(per_person, 2),
            "num_vehicles": 1,
            "feasible": True,
            "note": f"₹{round(per_person, 2)} per person (shared among {num_people})"
        }
    else:
        # Multiple vehicles needed
        num_vehicles = (num_people + vehicle_capacity - 1) // vehicle_capacity
        total_cost_all = total_cost * num_vehicles
        per_person = total_cost_all / num_people
        return {
            "total_cost": total_cost_all,
            "per_person_cost": round(per_person, 2),
            "num_vehicles": num_vehicles,
            "feasible": True,
            "note": f"₹{round(per_person, 2)} per person ({num_vehicles} vehicles needed)"
        }


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
    transit_lines: Dict[str, Any] = None,
    num_people: int = 1
) -> List[Dict[str, Any]]:
    """Build all available route options with comfort scores and per-person costs."""
    options = []
    surge = get_surge_multiplier()
    
    # Option 1: Metro (if available)
    transit_line = None
    if transit_lines:
        transit_line = find_transit_line(origin, destination, city, transit_lines)
    
    if transit_line and transit_line.get("type") == "metro":
        metro_time = int(duration_min * 0.7)  # Metro is usually faster
        metro_fare_per_person = min(60, max(15, int(distance_km * 4)))
        metro_total_cost = metro_fare_per_person * num_people
        
        options.append({
            "mode": "Metro",
            "line": transit_line.get("line", "Metro"),
            "route_info": transit_line.get("route", f"{origin} → {destination}"),
            "cost": metro_total_cost,
            "per_person_cost": metro_fare_per_person,
            "num_people": num_people,
            "time": metro_time + 10,  # Add walking time
            "walking_m": 400,  # Average walk to metro
            "transfers": transit_line.get("transfers", 0),
            "frequency": transit_line.get("frequency", "5-10 mins"),
            "ac": True,
            "capacity_note": f"₹{metro_fare_per_person} per person × {num_people} people = ₹{metro_total_cost}",
            "steps": [
                f"🚶 Walk to {origin} Metro Station (~5 mins)",
                f"🚇 Take {transit_line.get('line', 'Metro')} towards {destination}",
                f"📍 Get off at {destination} station",
                f"🚶 Walk to your destination (~5 mins)",
                f"💰 Total cost for {num_people} {'person' if num_people == 1 else 'people'}: ₹{metro_total_cost}"
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
        # Check if origin is actually on the route or needs intermediate transport
        route_info = bus_line.get('route', f"{origin} → {destination}")
        route_lower = route_info.lower()
        origin_lower = origin.lower()
        
        # Detect generic placeholder routes
        is_generic_route = (
            route_info == f"{origin} → {destination}" or
            route_info == f"{origin} - {destination}" or
            route_info.lower() == f"{origin_lower} → {destination.lower()}"
        )
        
        # Check if origin appears in the route
        origin_keywords = ['rvce', 'rv college', origin_lower.split()[0] if ' ' in origin_lower else origin_lower]
        origin_in_route = any(keyword in route_lower for keyword in origin_keywords)
        
        # If generic route or origin not in route, need intermediate transport
        need_intermediate_transport = is_generic_route or not origin_in_route
        
        # Calculate costs
        auto_cost_to_hub = 100 if need_intermediate_transport else 0
        bus_fare = 25
        bus_fare_per_person = auto_cost_to_hub + bus_fare
        bus_total_cost = bus_fare_per_person * num_people
        
        steps = []
        if need_intermediate_transport:
            steps.extend([
                f"🛺 Take auto to bus hub (~₹100, 5-8 mins)",
                f"🚶 Walk to bus stop at hub (~2 mins)"
            ])
        else:
            steps.append(f"🚶 Walk to nearest bus stop (~3 mins)")
        
        steps.extend([
            f"🚌 Take {bus_line.get('line', 'Bus')} towards {destination}",
            f"   💰 Bus fare: ₹{bus_fare} per person",
            f"📍 Get off near {destination}",
            f"🚶 Walk to your destination (~3 mins)",
            f"💰 Total cost for {num_people} {'person' if num_people == 1 else 'people'}: ₹{bus_total_cost}"
        ])
        
        if need_intermediate_transport:
            steps.append(f"   (₹{auto_cost_to_hub} auto + ₹{bus_fare * num_people} bus × {num_people} people)")
        
        options.append({
            "mode": "Bus",
            "line": bus_line.get("line", "Local Bus"),
            "route_info": bus_line.get("route", f"{origin} → {destination}"),
            "cost": bus_total_cost,
            "per_person_cost": bus_fare_per_person,
            "num_people": num_people,
            "time": int(duration_min * 1.5) + 10 + (8 if need_intermediate_transport else 0),
            "walking_m": 300,
            "transfers": 1 if need_intermediate_transport else 0,
            "frequency": bus_line.get("frequency", "15-20 mins"),
            "ac": False,
            "capacity_note": f"₹{bus_fare_per_person} per person × {num_people} people = ₹{bus_total_cost}",
            "needs_auto_to_hub": need_intermediate_transport,
            "steps": steps
        })
    
    # Option 3: Auto-rickshaw
    auto_base = 35
    auto_per_km = 18
    auto_single_cost = int((auto_base + distance_km * auto_per_km) * surge)
    auto_time = max(10, int(duration_min * 1.1))
    auto_capacity = VEHICLE_CAPACITY["auto"]
    auto_cost_info = calculate_per_person_cost(auto_single_cost, num_people, auto_capacity)
    
    if auto_cost_info["feasible"]:
        options.append({
            "mode": "Auto",
            "line": "Auto-rickshaw",
            "route_info": "Door-to-door service",
            "cost": auto_cost_info["total_cost"],
            "per_person_cost": auto_cost_info["per_person_cost"],
            "num_people": num_people,
            "num_vehicles": auto_cost_info["num_vehicles"],
            "time": auto_time,
            "walking_m": 0,
            "transfers": 0,
            "ac": False,
            "door_to_door": True,
            "capacity": f"{num_people}/{auto_capacity} per auto",
            "capacity_note": auto_cost_info["note"],
            "steps": [
                f"🛺 Book or hail {auto_cost_info['num_vehicles']} auto{'s' if auto_cost_info['num_vehicles'] > 1 else ''} from {origin}",
                f"👥 Maximum {auto_capacity} people per auto",
                f"💰 Total cost: ₹{auto_cost_info['total_cost']} ({auto_cost_info['note']})",
                f"📍 Direct ride to {destination}"
            ]
        })
    
    # Option 4: Cab (Ola/Uber) - Sedan (4 people) or SUV (6 people)
    cab_time = max(10, int(duration_min))
    
    # Sedan option (4 people max)
    sedan_cost = int((50 + distance_km * 15) * surge)
    sedan_capacity = VEHICLE_CAPACITY["sedan_cab"]
    sedan_cost_info = calculate_per_person_cost(sedan_cost, num_people, sedan_capacity)
    
    if sedan_cost_info["feasible"]:
        options.append({
            "mode": "Cab (Sedan)",
            "line": "Ola/Uber Sedan",
            "route_info": "AC, Door-to-door service",
            "cost": sedan_cost_info["total_cost"],
            "per_person_cost": sedan_cost_info["per_person_cost"],
            "num_people": num_people,
            "num_vehicles": sedan_cost_info["num_vehicles"],
            "time": cab_time + 5,
            "walking_m": 0,
            "transfers": 0,
            "ac": True,
            "door_to_door": True,
            "capacity": f"{num_people}/{sedan_capacity} per sedan",
            "capacity_note": sedan_cost_info["note"],
            "steps": [
                f"📱 Book {sedan_cost_info['num_vehicles']} sedan{'s' if sedan_cost_info['num_vehicles'] > 1 else ''} on Ola/Uber app",
                f"👥 Maximum {sedan_capacity} people per sedan",
                f"⏰ Wait for pickup (~5 mins)",
                f"🚗 AC ride to {destination}",
                f"💰 Total cost: ₹{sedan_cost_info['total_cost']} ({sedan_cost_info['note']})"
            ]
        })
    
    # SUV/XL option (6 people max) - only if needed
    if num_people > sedan_capacity or num_people >= 5:
        suv_cost = int((80 + distance_km * 20) * surge)  # Higher base and per km
        suv_capacity = VEHICLE_CAPACITY["suv_cab"]
        suv_cost_info = calculate_per_person_cost(suv_cost, num_people, suv_capacity)
        
        if suv_cost_info["feasible"]:
            options.append({
                "mode": "Cab (SUV/XL)",
                "line": "Ola/Uber XL",
                "route_info": "Large AC vehicle, Door-to-door",
                "cost": suv_cost_info["total_cost"],
                "per_person_cost": suv_cost_info["per_person_cost"],
                "num_people": num_people,
                "num_vehicles": suv_cost_info["num_vehicles"],
                "time": cab_time + 5,
                "walking_m": 0,
                "transfers": 0,
                "ac": True,
                "door_to_door": True,
                "capacity": f"{num_people}/{suv_capacity} per SUV",
                "capacity_note": suv_cost_info["note"],
                "steps": [
                    f"📱 Book {suv_cost_info['num_vehicles']} SUV/XL{'s' if suv_cost_info['num_vehicles'] > 1 else ''} on Ola/Uber app",
                    f"👥 Maximum {suv_capacity} people per SUV",
                    f"⏰ Wait for pickup (~5 mins)",
                    f"🚗 Large AC vehicle ride to {destination}",
                    f"💰 Total cost: ₹{suv_cost_info['total_cost']} ({suv_cost_info['note']})"
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
    transit_lines: Dict[str, Any] = None,
    num_people: int = 1
) -> Dict[str, Any]:
    """
    Plan routes for elderly users with comfort-ranked options.
    
    Returns all available options ranked by comfort score,
    with the most comfortable and fastest options highlighted.
    Shows per-person costs when traveling in groups.
    """
    # Build all available options
    all_options = _build_all_options(
        current_location, destination, city,
        distance_km, duration_min, transit_lines,
        num_people
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
    people_note = f" for {num_people} {'person' if num_people == 1 else 'people'}" if num_people > 1 else ""
    
    if most_comfortable:
        if most_comfortable["mode"] in ["Cab (Sedan)", "Cab (SUV/XL)", "Auto"]:
            recommendation = f"🌟 We recommend a {most_comfortable['mode']} for maximum comfort and door-to-door service{people_note}."
        else:
            recommendation = f"🌟 The most comfortable option is {most_comfortable['mode']} ({most_comfortable['line']}){people_note}."
    else:
        recommendation = "Please consider booking a cab for the safest journey."
    
    # Build formatted_response for frontend display
    formatted_response = {
        "origin": current_location,
        "destination": destination,
        "num_people": num_people,
        "most_comfortable": {
            "mode": most_comfortable["mode"],
            "cost": most_comfortable["cost"],
            "per_person_cost": most_comfortable.get("per_person_cost", most_comfortable["cost"]),
            "time": most_comfortable["time"],
            "steps": most_comfortable["steps"],
            "comfort_score": most_comfortable["comfort_score"],
            "highlighted": True,
            "badge": "🌟 MOST COMFORTABLE",
            "capacity_note": most_comfortable.get("capacity_note", "")
        } if most_comfortable else None,
        "cheapest": {
            "mode": min(ranked_options, key=lambda x: x["cost"])["mode"],
            "cost": min(ranked_options, key=lambda x: x["cost"])["cost"],
            "per_person_cost": min(ranked_options, key=lambda x: x["cost"]).get("per_person_cost", min(ranked_options, key=lambda x: x["cost"])["cost"]),
            "time": min(ranked_options, key=lambda x: x["cost"])["time"],
            "steps": min(ranked_options, key=lambda x: x["cost"])["steps"],
            "capacity_note": min(ranked_options, key=lambda x: x["cost"]).get("capacity_note", "")
        } if ranked_options else None,
        "fastest": {
            "mode": fastest["mode"],
            "cost": fastest["cost"],
            "per_person_cost": fastest.get("per_person_cost", fastest["cost"]),
            "time": fastest["time"],
            "steps": fastest["steps"],
            "capacity_note": fastest.get("capacity_note", "")
        } if fastest else None,
        "all_options": [
            {
                "mode": opt["mode"],
                "cost": opt["cost"],
                "per_person_cost": opt.get("per_person_cost", opt["cost"]),
                "time": opt["time"],
                "comfort_score": opt["comfort_score"],
                "ac": opt.get("ac", False),
                "door_to_door": opt.get("door_to_door", False),
                "walking_m": opt.get("walking_m", 0),
                "capacity_note": opt.get("capacity_note", "")
            }
            for opt in ranked_options
        ]
    }
    
    return {
        "mode": "elderly",
        "decision": "Comfort-ranked route options",
        "most_comfortable": most_comfortable,
        "fastest": fastest,
        "all_options": ranked_options,
        "formatted_response": formatted_response,
        "route": most_comfortable.get("line", "Cab recommended") if most_comfortable else "Cab recommended",
        "cost": most_comfortable["cost"] if most_comfortable else 100,
        "time": f"{most_comfortable['time']} mins" if most_comfortable else "20-30 mins",
        "explanation": recommendation + f"\n\n💡 Showing all available options with per-person costs{people_note}.",
        "distance_km": distance_km,
        "duration_min": duration_min,
        "num_people": num_people,
        "ride_options": ride_estimates.get("ride_options", []),
        "ride_recommendation": ride_estimates.get("recommendation", ""),
        "safety_note": "🛡️ For elderly travelers, we prioritize comfort, safety, and accessibility. The highlighted option offers the best balance for your needs."
    }
