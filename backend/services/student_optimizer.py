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
    """Find any bus route that connects origin and destination areas."""
    if not transit_lines:
        print(f"[BUS_FINDER] transit_lines is None")
        return None
    
    city_data = transit_lines.get("cities", {}).get(city, {})
    if "bus" not in city_data or "major_routes" not in city_data["bus"]:
        print(f"[BUS_FINDER] No bus routes found for city={city}")
        return None
    
    origin_lower = origin.lower()
    dest_lower = destination.lower()
    
    print(f"[BUS_FINDER] Looking for routes: {origin} → {destination}")
    
    # Common area mappings for better matching
    area_aliases = {
        "rvce": ["rv college", "rashtreeya vidyalaya", "mysore road", "kengeri", "electronic city"],
        "electronic city": ["silk board", "bommasandra", "rvce", "kengeri"],
        "ittamadu": ["banashankari", "jp nagar", "jayanagar"],
        "banashankari": ["bsk", "jp nagar", "jayanagar", "ittamadu"],
        "silk board": ["electronic city", "central silk board", "majestic"],
        "majestic": ["kempegowda", "kbs", "city railway station", "kempegowda bus station", "electronic city", "whitefield"],
        "kempegowda bus station": ["majestic", "kbs", "electronic city"],
        "hebbal": ["mekhri circle", "esteem mall", "majestic", "yelahanka"],
        "whitefield": ["majestic", "hebbal"],
    }
    
    # Get aliases for origin/destination
    origin_aliases = [origin_lower]
    dest_aliases = [dest_lower]
    for key, aliases in area_aliases.items():
        if key in origin_lower or origin_lower in key:
            origin_aliases.extend(aliases)
        if key in dest_lower or dest_lower in key:
            dest_aliases.extend(aliases)
    
    # Remove duplicates
    origin_aliases = list(set(origin_aliases))
    dest_aliases = list(set(dest_aliases))
    
    print(f"[BUS_FINDER] origin_aliases: {origin_aliases}")
    print(f"[BUS_FINDER] dest_aliases: {dest_aliases}")
    
    # Find routes that connect origin and destination
    # A route connects if:
    # 1. It mentions origin AND destination (best match)
    # 2. It mentions both via aliases (good match)
    # 3. It mentions destination and is on a major path from origin (acceptable match)
    
    best_route = None
    good_routes = []
    acceptable_routes = []
    
    for route in city_data["bus"]["major_routes"]:
        route_text = route["route"].lower()
        
        # Check origin matches
        origin_match = any(alias in route_text for alias in origin_aliases)
        # Check destination matches
        dest_match = any(alias in route_text for alias in dest_aliases)
        
        # Prioritize: both match > destination match > origin match
        if origin_match and dest_match:
            best_route = {
                'type': 'bus',
                'line': f"Bus {route['number']}",
                'route': route["route"],
                'frequency': route.get("frequency", "20-30 mins")
            }
            print(f"[BUS_FINDER] ✓ Best match: Route {route['number']}")
            break  # Found best match, use it
        elif dest_match:
            good_routes.append({
                'type': 'bus',
                'line': f"Bus {route['number']}",
                'route': route["route"],
                'frequency': route.get("frequency", "20-30 mins"),
                'score': 2
            })
            print(f"[BUS_FINDER] ✓ Good match: Route {route['number']} (destination match)")
        elif origin_match:
            acceptable_routes.append({
                'type': 'bus',
                'line': f"Bus {route['number']}",
                'route': route["route"],
                'frequency': route.get("frequency", "20-30 mins"),
                'score': 1
            })
            print(f"[BUS_FINDER] ◐ Acceptable match: Route {route['number']} (origin match)")
    
    if best_route:
        return best_route
    elif good_routes:
        return good_routes[0]  # Return first good match
    elif acceptable_routes:
        return acceptable_routes[0]  # Return first acceptable match
    else:
        print(f"[BUS_FINDER] ✗ No bus route found")
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


def _build_bus_directions(origin: str, destination: str, transit_line: Dict, distance_km: float, num_people: int = 1) -> Dict[str, Any]:
    """Build detailed step-by-step bus directions including how to reach the bus stop.
    
    Supports group travel - automatically multiplies costs by number of people.
    """
    bus_number = transit_line.get('line', 'Local Bus')
    route_info = transit_line.get('route', f'{origin} → {destination}')
    frequency = transit_line.get('frequency', '15-20 mins')
    freq_mins = _parse_frequency(frequency)
    next_bus = _get_next_departure_time(freq_mins)
    
    travel_time = _estimate_time(distance_km, 'bus')
    
    # Smart check: Does this bus route actually pass through the origin?
    origin_lower = origin.lower()
    route_lower = route_info.lower()
    dest_lower = destination.lower()
    
    # Check if this is a REAL route or a generic placeholder
    # Generic placeholder format: "Origin → Destination" or "Origin - Destination"
    is_generic_route = (
        route_info == f"{origin} → {destination}" or
        route_info == f"{origin} - {destination}" or
        route_info.lower() == f"{origin_lower} → {dest_lower}" or
        route_info.lower() == f"{origin_lower} - {dest_lower}"
    )
    
    # If it's a generic placeholder route, we CANNOT assume origin is covered
    # Real routes have specific bus numbers or intermediate stops
    if is_generic_route:
        origin_in_route = False  # Generic route = no direct bus
    else:
        # Check if origin appears in a REAL route
        origin_keywords = [
            origin_lower,
            origin_lower.split()[0] if ' ' in origin_lower else '',
            'rvce' if 'rvce' in origin_lower or 'rv college' in origin_lower else '',
            'rv college' if 'rvce' in origin_lower or 'rv college' in origin_lower else ''
        ]
        origin_keywords = [k for k in origin_keywords if k]
        origin_in_route = any(keyword in route_lower for keyword in origin_keywords)
    
    # If origin is NOT in the route, extract the bus starting point from route
    bus_start_point = "Majestic"  # Default hub
    if not origin_in_route and route_info:
        # Extract first location from route (e.g., "Majestic - Electronic City" → "Majestic")
        route_parts = route_info.replace('→', '-').split('-')
        if route_parts:
            bus_start_point = route_parts[0].strip()
    
    # Get specific bus stop names
    origin_stop = f"{origin} Bus Stop" if "bus stop" not in origin.lower() else origin
    bus_hub_stop = f"{bus_start_point} Bus Station"
    dest_stop = f"{destination} Bus Stop" if "bus stop" not in destination.lower() else destination
    
    # Calculate time breakdown
    auto_to_hub_time = 15  # Estimated auto/taxi time to reach bus starting point
    wait_time = freq_mins // 2  # Average wait time
    bus_ride_time = travel_time
    
    # Need intermediate transport ONLY if origin is NOT on the bus route
    need_intermediate_transport = not origin_in_route
    
    steps = []
    
    if need_intermediate_transport:
        # Bus doesn't pass through origin - need to reach the bus starting point first
        steps.extend([
            f"📍 STEP 1: Reach {bus_start_point} (Bus Starting Point)",
            f"🚶 Walk to nearest auto/taxi stand from {origin} (~2 mins)",
            f"   📍 Location: Find the auto/taxi stand near {origin} main road",
            f"🛺 Take auto/taxi from {origin} to {bus_start_point} (~{auto_to_hub_time} mins)",
            f"   💰 Cost: ~₹80-100 for auto, ~₹150-200 for cab",
            f"   📍 Ask driver to drop at {bus_start_point} bus station",
            f"",
            f"📍 STEP 2: Board Bus {bus_number} from {bus_start_point}",
        ])
    else:
        # Direct bus available from origin!
        steps.append(f"📍 STEP 1: Board Bus {bus_number} from {origin}")
    
    steps.extend([
        f"🚶 Walk to {origin_stop if not need_intermediate_transport else bus_hub_stop} (~2 mins)",
        f"   📍 Location: Look for the bus stop with {bus_number} buses",
        f"   🚶‍♂️ Find the area where {bus_number} stops",
        f"⏰ Wait for {bus_number} heading to {destination}",
        f"   🕐 Next bus approximately at {next_bus}",
        f"   ⏳ Average wait: {wait_time} mins (every {frequency})",
        f"🚌 Board {bus_number}",
        f"   💺 Journey time: ~{bus_ride_time} mins",
        f"   📍 Route: {route_info}",
        f"🛑 Get off at {dest_stop}",
        f"   🔔 Listen for station announcements or ask conductor/fellow passengers",
        f"",
        f"📍 {'STEP 3' if need_intermediate_transport else 'STEP 2'}: Reach your destination",
        f"🚶 Walk from {destination} bus stop to your final destination (~2 mins)",
        f"   📍 Head towards {destination} area",
        f"",
        f"⏱️ Total Journey Time: ~{(auto_to_hub_time + 2) if need_intermediate_transport else 0 + wait_time + bus_ride_time + 4} mins"
    ])
    
    # Calculate total cost: 
    # - If bus passes through origin: just bus fare (₹25 per person)
    # - If bus doesn't pass through origin: auto to bus start point + bus fare (per person)
    auto_cost_per_person = 100 if need_intermediate_transport else 0
    bus_fare_per_person = 25
    total_cost_per_person = auto_cost_per_person + bus_fare_per_person
    total_cost = total_cost_per_person * num_people
    
    return {
        "mode": "Bus",
        "route": bus_number,
        "route_info": route_info,
        "bus_start_point": bus_start_point if need_intermediate_transport else origin,
        "direct_bus_available": not need_intermediate_transport,
        "cost": total_cost,
        "per_person_cost": total_cost_per_person,
        "num_people": num_people,
        "group_cost_note": f"₹{total_cost_per_person} per person × {num_people} people = ₹{total_cost}" if num_people > 1 else "",
        "cost_breakdown": {
            "auto_to_hub": auto_cost_per_person,
            "bus_fare": bus_fare_per_person,
            "per_person": total_cost_per_person,
            "total": total_cost
        },
        "time": (auto_to_hub_time + 2 if need_intermediate_transport else 0) + wait_time + bus_ride_time + 4,
        "frequency": frequency,
        "next_departure": next_bus,
        "steps": steps,
        "steps_text": "\n".join(steps)
    }


def _build_metro_directions(origin: str, destination: str, transit_line: Dict, distance_km: float, num_people: int = 1) -> Dict[str, Any]:
    """Build detailed step-by-step metro directions. Supports group travel."""
    metro_line = transit_line.get('line', 'Metro')
    route_info = transit_line.get('route', f'{origin} → {destination}')
    frequency = transit_line.get('frequency', '5-10 mins')
    freq_mins = _parse_frequency(frequency)
    next_metro = _get_next_departure_time(freq_mins)
    
    travel_time = _estimate_time(distance_km, 'metro')
    
    # Estimate metro fare per person (roughly ₹4 per km, min ₹15, max ₹60)
    metro_fare_per_person = min(60, max(15, int(distance_km * 4)))
    metro_fare_total = metro_fare_per_person * num_people
    
    # Get station names
    origin_station = f"{origin} Metro Station" if "metro" not in origin.lower() else origin
    dest_station = f"{destination} Metro Station" if "metro" not in destination.lower() else destination
    
    # Calculate time breakdown
    walk_to_station_time = 3
    wait_time = freq_mins // 2
    metro_ride_time = travel_time
    walk_from_station_time = 3
    
    steps = [
        f"🚶 Walk to {origin_station} (3 mins)",
        f"   📍 Location: Find the nearest metro entrance with Purple Line signage",
        f"   🚶‍♂️ Look for metro station pillars and entrance gates",
        f"🎫 Purchase token/smart card (₹{metro_fare_per_person} per person)" + (f" × {num_people} people = ₹{metro_fare_total}" if num_people > 1 else ""),
        f"   💳 Use ticket counter or vending machine",
        f"⏰ Wait for {metro_line} train (avg wait: {wait_time} mins, every {frequency})",
        f"   🕐 Next train approximately at {next_metro}",
        f"🚇 Board metro towards {destination} direction",
        f"   📍 Check platform signs for correct direction",
        f"   💺 Journey time: ~{metro_ride_time} mins",
        f"   🚉 Route: {route_info}",
        f"   👥 Group: {num_people} {'person' if num_people == 1 else 'people'}",
        f"🚉 Alight at {dest_station}",
        f"   🔔 Listen for station announcements",
        f"🚶 Exit station and walk to {destination} (3 mins)",
        f"   📍 Follow exit signs towards {destination}",
        f"⏱️ Total time: ~{walk_to_station_time + wait_time + metro_ride_time + walk_from_station_time} mins"
    ]
    
    return {
        "mode": "Metro",
        "route": metro_line,
        "route_info": route_info,
        "cost": metro_fare_total,
        "per_person_cost": metro_fare_per_person,
        "num_people": num_people,
        "group_cost_note": f"₹{metro_fare_per_person} per person × {num_people} people = ₹{metro_fare_total}" if num_people > 1 else "",
        "time": travel_time + 6,  # Add walking time
        "frequency": frequency,
        "next_departure": next_metro,
        "steps": steps,
        "steps_text": "\n".join(steps)
    }


def _build_auto_directions(origin: str, destination: str, distance_km: float, city_fares: Dict, num_people: int = 1) -> Dict[str, Any]:
    """Build auto/cab directions."""
    surge = get_surge_multiplier()
    auto_base = city_fares.get("auto_base", 35)
    auto_per_km = city_fares.get("auto_per_km", 18)
    
    # Use ride-hailing estimator for realistic Auto pricing (keeps UI consistent)
    try:
        estimates = get_estimated_ride_prices(
            origin=origin,
            destination=destination,
            distance_km=distance_km,
            surge_multiplier=surge,
            user_type="student"
        )
        auto_options = [o for o in estimates.get("ride_options", []) if o.get("category") == "auto"]
        auto_options = sorted(auto_options, key=lambda x: x.get("estimated_price", 9_999_999))
        if auto_options:
            auto_cost = int(auto_options[0]["estimated_price"])  # cheapest auto from live-like table
        else:
            auto_cost = int((auto_base + (distance_km * auto_per_km)) * surge)
    except Exception:
        # Fallback to city fare model if estimator fails
        auto_cost = int((auto_base + (distance_km * auto_per_km)) * surge)
    
    # Include minimal booking/wait time to reflect door-to-door reality
    travel_time = _estimate_time(distance_km, 'auto')
    
    surge_text = " (peak hour surge)" if surge > 1 else ""
    
    # Calculate time breakdown
    booking_time = 2
    wait_time = 3
    ride_time = travel_time
    
    steps = [
        f"📱 Book auto/cab using app (2 mins)",
        f"   🚖 Open Uber/Ola/Rapido app",
        f"   📍 Set pickup: {origin}",
        f"   🎯 Set destination: {destination}",
        f"   💰 Expected fare: ₹{auto_cost}{surge_text}",
        f"⏰ Wait for driver arrival (avg 3 mins)",
        f"   📲 Track driver location in app",
        f"   📍 Stand at a visible pickup point near {origin}",
        f"🚗 Board the vehicle and confirm destination",
        f"   🗺️ Driver will follow GPS navigation",
        f"   ⏱️ Journey time: ~{ride_time} mins",
        f"   🛣️ Route will be optimized based on current traffic",
        f"📍 Arrive at {destination}",
        f"   💳 Complete payment via app or cash",
        f"⏱️ Total time: ~{booking_time + wait_time + ride_time} mins"
    ]
    
    return {
        "mode": "Auto",
        "route": "Direct door-to-door",
        "cost": auto_cost,
        "time": booking_time + wait_time + ride_time,
        "steps": steps,
        "steps_text": "\n".join(steps),
        "surge_active": surge > 1
    }


def _build_multimodal_directions(origin: str, destination: str, transit_line: Dict, distance_km: float, city_fares: Dict, num_people: int = 1) -> Dict[str, Any]:
    """Build multimodal (metro + bus) directions for better cost efficiency. Supports group travel."""
    hub = "Majestic"  # Default hub for Bengaluru
    if "Majestic" in transit_line.get('route', ''):
        hub = "Majestic"
    
    # Metro from origin to hub, then bus from hub to destination
    # Cost breakdown - Metro + Bus is more cost-effective than full auto
    # Metro fare: ₹20 flat for most journeys in Bengaluru metro
    # Bus fare: ₹25 flat
    metro_fare_per_person = min(60, max(15, int(distance_km * 2)))  # More realistic metro fare: ~₹20
    bus_fare_per_person = 25  # Bus portion (flat)
    total_cost_per_person = metro_fare_per_person + bus_fare_per_person
    total_cost = total_cost_per_person * num_people
    
    # Time breakdown
    metro_time = _estimate_time(distance_km * 0.4, 'metro')  # 40% of distance by metro
    bus_time = _estimate_time(distance_km * 0.6, 'bus')  # 60% of distance by bus
    total_time = metro_time + 5 + bus_time + 4  # Plus waiting and walking
    
    steps = [
        f"📍 STEP 1: Take Metro to {hub}",
        f"🚶 Walk to nearest Metro station from {origin} (~3 mins)",
        f"🚇 Take Metro towards {hub}",
        f"   💺 Journey time: ~{metro_time} mins",
        f"   💰 Metro fare: ₹{metro_fare_per_person} per person" + (f" × {num_people} = ₹{metro_fare_per_person * num_people}" if num_people > 1 else ""),
        f"👥 Group: {num_people} {'person' if num_people == 1 else 'people'}",
        f"🛑 Get off at {hub} Metro Station",
        f"",
        f"📍 STEP 2: Take Bus from {hub} to {destination}",
        f"🚶 Walk from {hub} Metro to Bus Station (~3 mins)",
        f"⏰ Wait for bus to {destination} (~5 mins avg)",
        f"🚌 Board bus heading towards {destination}",
        f"   💺 Journey time: ~{bus_time} mins",
        f"   💰 Bus fare: ₹{bus_fare_per_person} per person" + (f" × {num_people} = ₹{bus_fare_per_person * num_people}" if num_people > 1 else ""),
        f"🛑 Get off at {destination}",
        f"🚶 Walk to final destination (~2 mins)",
        f"",
        f"💰 Total Cost: ₹{total_cost} ({'₹' + str(metro_fare_per_person) + ' metro + ₹' + str(bus_fare_per_person) + ' bus per person' if num_people > 1 else '₹' + str(metro_fare_per_person) + ' metro + ₹' + str(bus_fare_per_person) + ' bus'})",
        f"⏱️ Total Time: ~{total_time} mins"
    ]
    
    return {
        "mode": "Metro + Bus",
        "route": f"{origin} → {hub} → {destination}",
        "route_info": f"Metro to {hub}, then bus to {destination}",
        "cost": total_cost,
        "per_person_cost": total_cost_per_person,
        "num_people": num_people,
        "group_cost_note": f"₹{total_cost_per_person} per person × {num_people} people = ₹{total_cost}" if num_people > 1 else "",
        "time": total_time,
        "steps": steps,
        "steps_text": "\n".join(steps),
        "cost_breakdown": {
            "metro_fare_per_person": metro_fare_per_person,
            "bus_fare_per_person": bus_fare_per_person,
            "per_person": total_cost_per_person,
            "total": total_cost
        }
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
            # Use proper bus directions that include cost of reaching bus hub
            bus_directions = _build_bus_directions(origin, destination, fallback_bus, distance_km or 5)
            all_options.append({
                'mode': bus_directions['mode'],
                'cost': bus_directions['cost'],  # Now includes auto to hub if needed
                'time': bus_directions['time'],
                'steps_text': bus_directions['steps_text'],
                'route_number': bus_directions['route'],
                'cost_breakdown': bus_directions.get('cost_breakdown', {})
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
    budget_limit: int = None,
    num_people: int = 1
) -> Dict[str, Any]:
    """
    Compute cheapest vs fastest route options with detailed step-by-step directions.
    Uses HybridRouter for real OpenCity transit data when available.
    
    Supports group travel - costs are calculated per person and total for the group.
    
    Returns dict with:
    - cheapest: Budget-friendly option (usually bus)
    - fastest: Quickest option (metro/auto)
    - door_to_door: Auto/cab for convenience
    - ride_options: Ride-hailing estimates
    - group_info: Group composition (num_people, per_person_cost, total_cost)
    """
    # Try HybridRouter first for real transit data from OpenCity.in
    if HYBRID_ROUTER_AVAILABLE:
        try:
            router = get_hybrid_router()
            hybrid_result = router.plan_route(home, destination, city, preferred_mode="auto")
            
            # If we got a good result with real transit data, use it
            if hybrid_result and hybrid_result.get('segments'):
                return _convert_hybrid_to_options(hybrid_result, home, destination, distance_km, fares, city, transit_lines, num_people)
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
    
    # ALWAYS prioritize DIFFERENT modes for cheapest vs fastest
    # This ensures users see distinct options with different trade-offs
    
    print(f"\n[COMPUTE_OPTIONS] Starting route computation for {home} -> {destination} | Group size: {num_people}")
    print(f"[COMPUTE_OPTIONS] Distance: {distance_km}km, City: {city}, Transit lines available: {transit_lines is not None}")
    
    # =======================================================================
    # STEP 1: Build ALL possible route options
    # =======================================================================
    all_route_options = []
    
    # Option 1: Bus route (direct or via hub)
    print(f"\n[STEP 1] Checking BUS routes...")
    if transit_lines:
        fallback_bus = _find_nearby_bus(home, destination, city, transit_lines)
        if fallback_bus:
            print(f"  ✓ Found bus route: {fallback_bus['line']}")
            bus_route = _build_bus_directions(home, destination, fallback_bus, distance_km, num_people)
            all_route_options.append(bus_route)
        else:
            print(f"  ✗ No bus route found")
    
    # Option 2: Metro route (if available)
    print(f"\n[STEP 2] Checking METRO routes...")
    if transit_line and transit_line['type'] in ['metro', 'suburban_rail']:
        print(f"  ✓ Found metro/rail: {transit_line['line']}")
        metro_route = _build_metro_directions(home, destination, transit_line, distance_km, num_people)
        all_route_options.append(metro_route)
    else:
        # Try to find metro line
        if transit_lines:
            city_data = transit_lines.get("cities", {}).get(city, {})
            if "metro" in city_data:
                for line in city_data["metro"]["lines"]:
                    # Simple check if both origin and destination could be near metro
                    route_lower = line["route"].lower()
                    if any(kw in route_lower for kw in [home.lower().split()[0], 'all stations']):
                        print(f"  ✓ Metro line possible: {line['name']}")
                        metro_route = _build_metro_directions(home, destination, line, distance_km, num_people)
                        all_route_options.append(metro_route)
                        break
        print(f"  → Metro options: {len([o for o in all_route_options if o['mode'] in ['Metro', 'Suburban Rail']])}")
    
    # Option 3: Metro + Bus combination
    print(f"\n[STEP 3] Checking METRO + BUS combination...")
    metro_plus_bus = _build_multimodal_directions(home, destination, 
                                                  {'line': 'Metro', 'route': f'{home} → Majestic'}, 
                                                  distance_km, city_fares, num_people)
    all_route_options.append(metro_plus_bus)
    print(f"  ✓ Metro+Bus: ₹{metro_plus_bus['cost']} in {metro_plus_bus['time']} mins")
    
    # Option 4: Auto (direct)
    print(f"\n[STEP 4] Checking AUTO routes...")
    auto_route = _build_auto_directions(home, destination, distance_km, city_fares, num_people)
    all_route_options.append(auto_route)
    print(f"  ✓ Auto: ₹{auto_route['cost']} in {auto_route['time']} mins")
    
    # Option 5: Cab/Sedan (for comfort)
    print(f"\n[STEP 5] Checking CAB routes...")
    cab_cost_per_person = int((city_fares.get("cab_base", 50) + (distance_km * city_fares.get("cab_per_km", 22))) * surge)
    cab_cost = cab_cost_per_person * num_people
    cab_time = max(10, int((distance_km / 25) * 60))  # Cabs slightly faster than auto
    cab_route = {
        "mode": "Cab",
        "route": "Direct door-to-door",
        "cost": cab_cost,
        "per_person_cost": cab_cost_per_person,
        "num_people": num_people,
        "group_cost_note": f"₹{cab_cost_per_person} per person × {num_people} people = ₹{cab_cost}" if num_people > 1 else "",
        "time": cab_time,
        "steps": [
            f"📱 Book cab via Uber/Ola/Namma Yatri",
            f"🚗 Direct ride from {home} to {destination}",
            f"💰 Estimated: ₹{cab_cost} ({f'₹{cab_cost_per_person} per person' if num_people > 1 else 'per person'}) | ⏱️ ~{cab_time} mins",
            f"✨ AC comfort, luggage space",
            f"👥 Group: {num_people} {'person' if num_people == 1 else 'people'}"
        ],
        "steps_text": f"Book cab: Direct {home} → {destination}\nCost: ₹{cab_cost} ({f'₹{cab_cost_per_person}/person' if num_people > 1 else ''}), Time: ~{cab_time} mins, Group: {num_people} people"
    }
    all_route_options.append(cab_route)
    print(f"  ✓ Cab: ₹{cab_cost} in {cab_time} mins")
    
    # =======================================================================
    # STEP 2: Analyze and find ACTUAL cheapest, fastest, most comfortable
    # =======================================================================
    print(f"\n[ANALYSIS] Comparing {len(all_route_options)} route options...")
    print(f"[DEBUG] All options before sorting:")
    for opt in all_route_options:
        print(f"  - {opt['mode']}: ₹{opt.get('cost', 'N/A')} in {opt.get('time', 'N/A')} mins | Group: {num_people}")
    
    # Sort by cost (cheapest first)
    sorted_by_cost = sorted(all_route_options, key=lambda x: x.get('cost', 999999))
    cheapest = sorted_by_cost[0]
    print(f"  💰 CHEAPEST: {cheapest['mode']} - ₹{cheapest['cost']} ({f'₹{cheapest['cost']//num_people} per person' if num_people > 1 else 'per person'})")
    
    # Sort by time (fastest first)
    sorted_by_time = sorted(all_route_options, key=lambda x: x.get('time', 999999))
    fastest = sorted_by_time[0]
    print(f"  ⚡ FASTEST: {fastest['mode']} - {fastest['time']} mins")
    
    # Most balanced (best cost/time ratio)
    for option in all_route_options:
        option['cost_per_min'] = option['cost'] / max(option['time'], 1)
    sorted_by_balance = sorted(all_route_options, key=lambda x: x.get('cost_per_min', 999))
    balanced = sorted_by_balance[0]
    print(f"  ⚖️ BALANCED: {balanced['mode']} - ₹{balanced['cost']}/{balanced['time']}min")
    
    # Most comfortable (AC vehicles preferred)
    comfort_scores = []
    for option in all_route_options:
        score = 0
        if option['mode'] in ['Cab', 'SUV']: score = 100
        elif option['mode'] == 'Auto': score = 60
        elif option['mode'] == 'Metro': score = 80
        elif option['mode'] == 'Metro + Bus': score = 70
        elif option['mode'] == 'Bus': score = 50
        comfort_scores.append((option, score))
    most_comfortable = max(comfort_scores, key=lambda x: x[1])[0]
    print(f"  ✨ COMFORTABLE: {most_comfortable['mode']}")
    
    # Door-to-door option (prefer cab over auto for comfort)
    door_to_door = cab_route if cab_route in all_route_options else auto_route
    
    # Get ride-hailing estimates
    ride_estimates = get_estimated_ride_prices(
        origin=home,
        destination=destination,
        distance_km=distance_km,
        surge_multiplier=surge,
        user_type="student",
        budget_limit=budget_limit
    )
    
    # =======================================================================
    # STEP 3: Return comprehensive results
    # =======================================================================
    return {
        "cheapest": cheapest,
        "fastest": fastest,
        "balanced": balanced,
        "most_comfortable": most_comfortable,
        "door_to_door": door_to_door,
        "all_options": all_route_options,
        "ride_options": ride_estimates.get("ride_options", []),
        "ride_recommendation": ride_estimates.get("recommendation", ""),
        "recommendation": f"💰 Cheapest: {cheapest['mode']} (₹{cheapest['cost']}) | ⚡ Fastest: {fastest['mode']} ({fastest['time']}min) | ⚖️ Balanced: {balanced['mode']}",
        "group_info": {
            "num_people": num_people,
            "is_group": num_people > 1,
            "cheapest_per_person": cheapest['cost'] // num_people if num_people > 0 else cheapest['cost'],
            "fastest_per_person": fastest['cost'] // num_people if num_people > 0 else fastest['cost'],
            "group_note": f"🎫 Prices shown are total for {num_people} {'person' if num_people == 1 else 'people'}"
        },
        "distance_km": distance_km,
        "duration_min": duration_min,
        "surge_active": surge > 1,
        "analysis": {
            "total_options_found": len(all_route_options),
            "cheapest_cost": cheapest['cost'],
            "fastest_time": fastest['time'],
            "cost_range": f"₹{sorted_by_cost[0]['cost']} - ₹{sorted_by_cost[-1]['cost']}",
            "time_range": f"{sorted_by_time[0]['time']} - {sorted_by_time[-1]['time']} mins"
        }
    }
