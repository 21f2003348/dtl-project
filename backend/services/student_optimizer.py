"""
Student Route Optimizer - Computes cheapest vs fastest route options with detailed directions.
Uses HybridRouter for real transit data from OpenCity.in when available.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from services.transit_lookup import find_transit_line, suggest_multimodal_route, get_surge_multiplier
from services.ride_pricing import get_estimated_ride_prices

# Try to import HybridRouter (may not be available during testing)
try:
    from services.hybrid_router import get_hybrid_router, HybridRouter
    HYBRID_ROUTER_AVAILABLE = True
except ImportError:
    HYBRID_ROUTER_AVAILABLE = False
    HybridRouter = None


def _find_nearby_bus(origin: str, destination: str, city: str, transit_lines: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find any bus route that passes through BOTH origin and destination areas."""
    if not transit_lines:
        return None
    
    city_data = transit_lines.get("cities", {}).get(city, {})
    if "bus" not in city_data or "major_routes" not in city_data["bus"]:
        return None
    
    origin_lower = origin.lower()
    dest_lower = destination.lower()
    
    # Common area mappings for better matching
    area_aliases = {
        "rvce": ["rv college", "rashtreeya vidyalaya", "mysore road", "kengeri"],
        "ittamadu": ["banashankari", "jp nagar", "jayanagar"],
        "banashankari": ["bsk", "jp nagar", "jayanagar"],
        "majestic": ["kempegowda", "kbs", "city railway station", "kempegowda bus station"],
        "kempegowda bus station": ["majestic", "kbs"],
        "electronic city": ["silk board", "bommasandra"],
        "hebbal": ["mekhri circle", "esteem mall"],
    }
    
    # Get aliases for origin/destination
    origin_aliases = [origin_lower]
    dest_aliases = [dest_lower]
    for key, aliases in area_aliases.items():
        if key in origin_lower or origin_lower in key:
            origin_aliases.extend(aliases)
        if key in dest_lower or dest_lower in key:
            dest_aliases.extend(aliases)
    
    # First try: routes that match BOTH origin AND destination
    for route in city_data["bus"]["major_routes"]:
        route_text = route["route"].lower()
        origin_match = any(alias in route_text for alias in origin_aliases)
        dest_match = any(alias in route_text for alias in dest_aliases)
        
        if origin_match and dest_match:
            return {
                'type': 'bus',
                'line': f"Bus {route['number']}",
                'route': route["route"],
                'frequency': route.get("frequency", "20-30 mins")
            }
    
    # No fallback - if we can't find a route that covers both, return None
    # This forces the caller to suggest auto/cab instead of a wrong bus
    return None


def _estimate_time(distance_km: float, mode: str) -> int:
    """Estimate travel time in minutes based on distance and mode."""
    speed_map = {
        "bus": 15,        # 15 km/h average (accounting for stops)
        "metro": 35,      # 35 km/h average
        "auto": 20,       # 20 km/h in city traffic
        "walk": 5         # 5 km/h walking
    }
    speed = speed_map.get(mode, 15)
    return max(5, int((distance_km / speed) * 60))


def _get_next_departure_time(frequency_mins: int) -> str:
    """Calculate approximate next departure time based on frequency."""
    now = datetime.now()
    # Round up to next departure
    mins_to_next = frequency_mins - (now.minute % frequency_mins) if frequency_mins > 0 else 5
    next_time = now + timedelta(minutes=mins_to_next)
    return next_time.strftime("%H:%M")


def _parse_frequency(frequency_str: str) -> int:
    """Parse frequency string like '15 mins' or '10-20 mins' to average minutes."""
    import re
    numbers = re.findall(r'\d+', frequency_str)
    if numbers:
        return sum(int(n) for n in numbers) // len(numbers)
    return 15  # default 15 mins


def _build_bus_directions(origin: str, destination: str, transit_line: Dict, distance_km: float) -> Dict[str, Any]:
    """Build detailed step-by-step bus directions."""
    bus_number = transit_line.get('line', 'Local Bus')
    route_info = transit_line.get('route', f'{origin} → {destination}')
    frequency = transit_line.get('frequency', '15-20 mins')
    freq_mins = _parse_frequency(frequency)
    next_bus = _get_next_departure_time(freq_mins)
    
    travel_time = _estimate_time(distance_km, 'bus')
    
    steps = [
        f"🚶 Walk to {origin} Bus Stop (~2 mins)",
        f"🚌 Take {bus_number} towards {destination}",
        f"⏰ Next bus at approximately {next_bus} (every {frequency})",
        f"📍 Get off at {destination} stop (~{travel_time} mins ride)",
        f"🚶 Walk to your destination (~2 mins)"
    ]
    
    return {
        "mode": "Bus",
        "route": bus_number,
        "route_info": route_info,
        "cost": 25,  # Flat fare
        "time": travel_time + 4,  # Add walking time
        "frequency": frequency,
        "next_departure": next_bus,
        "steps": steps,
        "steps_text": "\n".join(steps)
    }


def _build_metro_directions(origin: str, destination: str, transit_line: Dict, distance_km: float) -> Dict[str, Any]:
    """Build detailed step-by-step metro directions."""
    metro_line = transit_line.get('line', 'Metro')
    route_info = transit_line.get('route', f'{origin} → {destination}')
    frequency = transit_line.get('frequency', '5-10 mins')
    freq_mins = _parse_frequency(frequency)
    next_metro = _get_next_departure_time(freq_mins)
    
    travel_time = _estimate_time(distance_km, 'metro')
    
    # Estimate metro fare (roughly ₹4 per km, min ₹15, max ₹60)
    metro_fare = min(60, max(15, int(distance_km * 4)))
    
    steps = [
        f"🚶 Walk to {origin} Metro Station (~3 mins)",
        f"🚇 Take {metro_line}",
        f"⏰ Next train at approximately {next_metro} (every {frequency})",
        f"📍 Get off at station nearest to {destination} (~{travel_time} mins ride)",
        f"🚶 Walk to your destination (~3 mins)"
    ]
    
    return {
        "mode": "Metro",
        "route": metro_line,
        "route_info": route_info,
        "cost": metro_fare,
        "time": travel_time + 6,  # Add walking time
        "frequency": frequency,
        "next_departure": next_metro,
        "steps": steps,
        "steps_text": "\n".join(steps)
    }


def _build_auto_directions(origin: str, destination: str, distance_km: float, city_fares: Dict) -> Dict[str, Any]:
    """Build auto/cab directions."""
    surge = get_surge_multiplier()
    auto_base = city_fares.get("auto_base", 35)
    auto_per_km = city_fares.get("auto_per_km", 18)
    
    auto_cost = int((auto_base + (distance_km * auto_per_km)) * surge)
    travel_time = _estimate_time(distance_km, 'auto')
    
    surge_text = " (peak hour surge)" if surge > 1 else ""
    
    steps = [
        f"🚗 Book an auto/cab from {origin}",
        f"💰 Estimated fare: ₹{auto_cost}{surge_text}",
        f"⏱️ Estimated travel time: ~{travel_time} mins",
        f"📍 Direct door-to-door service to {destination}"
    ]
    
    return {
        "mode": "Auto",
        "route": "Direct door-to-door",
        "cost": auto_cost,
        "time": travel_time,
        "steps": steps,
        "steps_text": "\n".join(steps),
        "surge_active": surge > 1
    }


def _build_multimodal_directions(origin: str, destination: str, transit_line: Dict, distance_km: float, city_fares: Dict) -> Dict[str, Any]:
    """Build multimodal (auto + metro/bus) directions."""
    hub = "Majestic"  # Default hub for Bengaluru
    if "Majestic" in transit_line.get('route', ''):
        hub = "Majestic"
    
    # Cost breakdown
    auto_to_hub = city_fares.get("auto_base", 35) + 50  # Auto to hub (~3km)
    metro_fare = 25  # Metro portion
    total_cost = auto_to_hub + metro_fare
    
    # Time breakdown
    auto_time = 10  # Auto to hub
    metro_time = _estimate_time(distance_km * 0.6, 'metro')  # 60% of distance by metro
    total_time = auto_time + metro_time + 5  # Plus waiting
    
    steps = [
        f"🚗 Take auto from {origin} to {hub} Metro (~₹{auto_to_hub}, 10 mins)",
        f"🚇 Take Metro from {hub} towards {destination}",
        f"📍 Get off at station nearest to {destination} (~{metro_time} mins)",
        f"🚶 Walk to your destination (~3 mins)"
    ]
    
    return {
        "mode": "Auto + Metro",
        "route": f"Via {hub}",
        "cost": total_cost,
        "time": total_time,
        "steps": steps,
        "steps_text": "\n".join(steps)
    }


def _convert_hybrid_to_options(hybrid_result: Dict[str, Any], origin: str, destination: str,
                                distance_km: float, fares: Dict[str, Any], city: str,
                                transit_lines: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convert HybridRouter result to standard compute_options format."""
    # Normalize city to title case for matching transit_lines.json keys
    city = city.title() if city else "Bengaluru"
    
    segments = hybrid_result.get('segments', [])
    total_time = hybrid_result.get('total_time', 30)
    total_cost = hybrid_result.get('total_cost', 25)
    mode = hybrid_result.get('mode', 'Transit')
    steps_text = hybrid_result.get('steps_text', '')
    alternatives = hybrid_result.get('alternatives', [])
    
    # Collect all route options (main result + alternatives)
    all_options = [{
        'mode': mode,
        'cost': total_cost,
        'time': total_time,
        'steps_text': steps_text,
        'segments': segments,
        'from_stop': hybrid_result.get('from_stop', ''),
        'to_stop': hybrid_result.get('to_stop', ''),
        'route_number': hybrid_result.get('route_number', mode)
    }]
    
    for alt in alternatives:
        all_options.append({
            'mode': alt.get('mode', 'Auto'),
            'cost': alt.get('total_cost', 100),
            'time': alt.get('total_time', 30),
            'steps_text': alt.get('steps_text', '')
        })
    
    # Add auto option if not already present
    surge = get_surge_multiplier()
    city_fares = fares.get("cities", {}).get(city, {})
    auto_cost = int((city_fares.get("auto_base", 35) + ((distance_km or 5) * city_fares.get("auto_per_km", 18))) * surge)
    auto_time = max(10, int(((distance_km or 5) / 20) * 60))
    
    has_auto = any(opt['mode'] == 'Auto' for opt in all_options)
    if not has_auto:
        all_options.append({
            'mode': 'Auto',
            'cost': auto_cost,
            'time': auto_time,
            'steps_text': f"🛺 Take auto from {origin} to {destination}\n⏱️ ~{auto_time} min | 💰 ₹{auto_cost}"
        })
    
    # ALWAYS try to add bus from static data if no Bus option exists
    # This ensures we show a cheap bus option even when HybridRouter only returns Auto
    has_bus = any(opt['mode'] == 'Bus' for opt in all_options)
    print(f"[DEBUG] has_bus={has_bus}, transit_lines is None={transit_lines is None}, city={city}")
    if not has_bus and transit_lines:
        fallback_bus = _find_nearby_bus(origin, destination, city, transit_lines)
        print(f"[DEBUG] fallback_bus result: {fallback_bus}")
        if fallback_bus:
            bus_time = _estimate_time(distance_km or 5, 'bus')
            all_options.append({
                'mode': 'Bus',
                'cost': 25,  # Flat BMTC fare
                'time': bus_time + 4,  # Add walking time
                'steps_text': f"🚌 Take {fallback_bus['line']} to {destination}\n📍 Route: {fallback_bus['route']}\n⏱️ Every {fallback_bus['frequency']} | 💰 ₹25",
                'route_number': fallback_bus['line']
            })
    
    # Filter out Walk mode - no one wants to walk in city traffic/heat
    all_options = [opt for opt in all_options if opt['mode'] != 'Walk']
    
    # Sort correctly: CHEAPEST = lowest cost, FASTEST = lowest time
    sorted_by_cost = sorted(all_options, key=lambda x: x['cost'])
    sorted_by_time = sorted(all_options, key=lambda x: x['time'])
    
    cheapest_opt = sorted_by_cost[0] if sorted_by_cost else all_options[0]
    fastest_opt = sorted_by_time[0] if sorted_by_time else all_options[0]
    
    # Build cheapest option (lowest cost - usually Walk or Bus)
    cheapest = {
        "mode": cheapest_opt['mode'],
        "route": cheapest_opt.get('route_number', cheapest_opt['mode']),
        "route_info": f"{origin} → {destination}",
        "cost": cheapest_opt['cost'],
        "time": cheapest_opt['time'],
        "steps": [seg.get('instruction', '') for seg in cheapest_opt.get('segments', [])],
        "steps_text": cheapest_opt['steps_text'],
        "from_stop": cheapest_opt.get('from_stop', ''),
        "to_stop": cheapest_opt.get('to_stop', '')
    }
    
    # Build fastest option (lowest time - usually Auto)
    fastest = {
        "mode": fastest_opt['mode'],
        "route": fastest_opt.get('route_number', fastest_opt['mode']),
        "cost": fastest_opt['cost'],
        "time": fastest_opt['time'],
        "steps_text": fastest_opt['steps_text']
    }
    
    # Door-to-door auto option
    surge = get_surge_multiplier()
    city_fares = fares.get("cities", {}).get(city, {})
    auto_cost = int((city_fares.get("auto_base", 35) + ((distance_km or 5) * city_fares.get("auto_per_km", 18))) * surge)
    auto_time = max(10, int(((distance_km or 5) / 20) * 60))
    door_to_door = {
        "mode": "Auto",
        "route": "Direct door-to-door",
        "cost": auto_cost,
        "time": auto_time,
        "steps_text": f"🛺 Take auto/cab from {origin} to {destination}\n⏱️ ~{auto_time} min | 💰 ₹{auto_cost}"
    }
    
    # Get ride estimates
    ride_estimates = get_estimated_ride_prices(
        origin=origin,
        destination=destination,
        distance_km=distance_km or 5,
        surge_multiplier=surge,
        user_type="student"
    )
    
    return {
        "cheapest": cheapest,
        "fastest": fastest,
        "door_to_door": door_to_door,
        "all_options": all_options,  # Full list for transparency
        "ride_options": ride_estimates.get("ride_options", []),
        "ride_recommendation": ride_estimates.get("recommendation", ""),
        "recommendation": f"Cheapest: {cheapest['mode']} at ₹{cheapest['cost']} | Fastest: {fastest['mode']} in {fastest['time']} mins",
        "distance_km": distance_km or 5,
        "duration_min": total_time,
        "surge_active": surge > 1,
        "data_source": "opencity"  # Mark as real data
    }



def compute_options(
    home: str, 
    destination: str, 
    city: str, 
    fares: Dict[str, Any], 
    distance_km: float = None, 
    duration_min: float = None, 
    transit_lines: Dict[str, Any] = None, 
    budget_limit: int = None
) -> Dict[str, Any]:
    """
    Compute cheapest vs fastest route options with detailed step-by-step directions.
    Uses HybridRouter for real OpenCity transit data when available.
    
    Returns dict with:
    - cheapest: Budget-friendly option (usually bus)
    - fastest: Quickest option (metro/auto)
    - door_to_door: Auto/cab for convenience
    - ride_options: Ride-hailing estimates
    """
    # Try HybridRouter first for real transit data from OpenCity.in
    if HYBRID_ROUTER_AVAILABLE:
        try:
            router = get_hybrid_router()
            hybrid_result = router.plan_route(home, destination, city, preferred_mode="auto")
            
            # If we got a good result with real transit data, use it
            if hybrid_result and hybrid_result.get('segments'):
                return _convert_hybrid_to_options(hybrid_result, home, destination, distance_km, fares, city, transit_lines)
        except Exception as e:
            print(f"[STUDENT_OPTIMIZER] HybridRouter error, falling back to static: {e}")
    
    # Handle None values with sensible defaults and sanity bounds
    if distance_km is None or distance_km <= 0:
        distance_km = 5.0  # Default 5km
    elif distance_km > 100:
        # Cap at 100km for city travel - anything larger is likely an error
        print(f"[STUDENT_OPTIMIZER] Warning: distance_km={distance_km} seems too large, capping at 30km")
        distance_km = 30.0
    
    if duration_min is None or duration_min <= 0:
        duration_min = distance_km * 3  # Estimate ~3 mins per km
    elif duration_min > 300:
        # Cap at 5 hours - anything larger is likely an error
        print(f"[STUDENT_OPTIMIZER] Warning: duration_min={duration_min} seems too large, using estimate")
        duration_min = distance_km * 3
    
    city_fares = fares.get("cities", {}).get(city, {})
    surge = get_surge_multiplier()
    
    # Try to find actual transit line
    transit_line = None
    if transit_lines:
        transit_line = find_transit_line(home, destination, city, transit_lines)
        if not transit_line:
            transit_line = suggest_multimodal_route(home, destination, city, transit_lines, distance_km)
    
    # Build cheapest option (Bus)
    if transit_line and transit_line['type'] == 'bus':
        cheapest = _build_bus_directions(home, destination, transit_line, distance_km)
    else:
        # Try to find any bus route that passes through the origin or destination
        fallback_bus = _find_nearby_bus(home, destination, city, transit_lines)
        if fallback_bus:
            cheapest = _build_bus_directions(home, destination, fallback_bus, distance_km)
        else:
            # Last resort: suggest checking the BMTC app
            default_bus = {
                'type': 'bus',
                'line': 'BMTC Bus (check app for route)',
                'route': f'{home} → {destination}',
                'frequency': '15-20 mins',
                'note': 'Share your location via Google Maps for precise bus info'
            }
            cheapest = _build_bus_directions(home, destination, default_bus, distance_km)
    
    # Build fastest option (Metro if available, else Auto)
    if transit_line and transit_line['type'] in ['metro', 'suburban_rail']:
        fastest = _build_metro_directions(home, destination, transit_line, distance_km)
    elif transit_line and transit_line['type'] == 'multimodal':
        fastest = _build_multimodal_directions(home, destination, transit_line, distance_km, city_fares)
    else:
        # Default to auto for fastest
        fastest = _build_auto_directions(home, destination, distance_km, city_fares)
    
    # Build door-to-door auto option
    door_to_door = _build_auto_directions(home, destination, distance_km, city_fares)
    
    # Get ride-hailing estimates
    ride_estimates = get_estimated_ride_prices(
        origin=home,
        destination=destination,
        distance_km=distance_km,
        surge_multiplier=surge,
        user_type="student",
        budget_limit=budget_limit
    )
    
    # Build all options list
    all_options = [cheapest, fastest]
    if door_to_door["mode"] != fastest["mode"]:
        all_options.append(door_to_door)
    
    return {
        "cheapest": cheapest,
        "fastest": fastest,
        "door_to_door": door_to_door,
        "all_options": all_options,
        "ride_options": ride_estimates.get("ride_options", []),
        "ride_recommendation": ride_estimates.get("recommendation", ""),
        "recommendation": f"Cheapest: {cheapest['mode']} at ₹{cheapest.get('cost', 25)} | Fastest: {fastest['mode']} in {fastest.get('time', 20)} mins",
        "distance_km": distance_km,
        "duration_min": duration_min,
        "surge_active": surge > 1
    }
