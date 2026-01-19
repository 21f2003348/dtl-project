"""
Hybrid Router combining walking (Mapbox) with public transit (OpenCity data).
Provides multi-modal routing: Walk -> Transit -> Walk
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

from services.transit_data_service import get_transit_service, TransitDataService
from services.mapbox_directions import get_mapbox_directions, get_mapbox_geocoder, MapboxDirections


class HybridRouter:
    """
    Multi-modal route planner combining walking and public transit.
    Supports: Walking, Bus, Metro, Auto/Taxi
    """
    
    def __init__(self, transit_service: Optional[TransitDataService] = None,
                 directions: Optional[MapboxDirections] = None):
        self.transit = transit_service or get_transit_service()
        self.directions = directions or get_mapbox_directions()
        self.geocoder = get_mapbox_geocoder()
    
    def plan_route(self, origin: str, destination: str, 
                   city: str = None, preferred_mode: str = "auto") -> Dict:
        """
        Plan a multi-modal route from origin to destination.
        
        Args:
            origin: Starting location name
            destination: Ending location name
            city: City (auto-detected if not provided)
            preferred_mode: 'bus', 'metro', 'auto' (picks best), 'walk'
            
        Returns:
            Multi-modal route with segments, times, and costs
        """
        # Auto-detect city if not provided
        if not city:
            city = self.transit.get_city_from_location(f"{origin} {destination}")
        
        # Get coordinates for origin and destination
        origin_coords = self._get_coordinates(origin, city)
        dest_coords = self._get_coordinates(destination, city)
        
        if not origin_coords or not dest_coords:
            return self._basic_route(origin, destination, city, preferred_mode)
        
        # Calculate straight-line distance
        straight_dist = self._haversine(
            origin_coords[1], origin_coords[0], 
            dest_coords[1], dest_coords[0]
        )
        
        # For very short distances, just walk
        if straight_dist < 0.5 and preferred_mode != "transit":
            return self._walking_only_route(origin, destination, origin_coords, dest_coords)
        
        # Find best transit options
        routes = []
        
        if preferred_mode in ["bus", "auto"]:
            bus_route = self._plan_bus_route(origin, destination, city, origin_coords, dest_coords)
            if bus_route:
                routes.append(bus_route)
        
        if preferred_mode in ["metro", "auto"] and city == "bengaluru":
            metro_route = self._plan_metro_route(origin, destination, city, origin_coords, dest_coords)
            if metro_route:
                routes.append(metro_route)
        
        # Always include walking option
        walk_route = self._walking_only_route(origin, destination, origin_coords, dest_coords)
        routes.append(walk_route)
        
        # Include auto/taxi option
        auto_route = self._auto_route(origin, destination, origin_coords, dest_coords, city)
        routes.append(auto_route)
        
        # Sort by time and pick best
        routes.sort(key=lambda x: x.get('total_time', 999))
        
        best = routes[0] if routes else self._basic_route(origin, destination, city, preferred_mode)
        
        return {
            **best,
            "alternatives": routes[1:3] if len(routes) > 1 else [],
            "city": city,
            "query": {"origin": origin, "destination": destination}
        }
    
    def _plan_bus_route(self, origin: str, destination: str, city: str,
                        origin_coords: Tuple, dest_coords: Tuple) -> Optional[Dict]:
        """Plan a route using bus."""
        # Find nearest bus stops
        origin_stop = self.transit.find_nearest_stop(
            origin_coords[1], origin_coords[0], city, "bus", max_distance_km=1.5
        )
        dest_stop = self.transit.find_nearest_stop(
            dest_coords[1], dest_coords[0], city, "bus", max_distance_km=1.5
        )
        
        if not origin_stop or not dest_stop:
            return None
        
        # Find bus routes between stops
        bus_routes = self.transit.find_routes_between(
            origin_stop['name'], dest_stop['name'], city, "bus"
        )
        
        if not bus_routes:
            return None
        
        best_bus = bus_routes[0]
        
        # Get walking segments
        walk_to_stop = self.directions.get_walking_route(
            origin_coords, (origin_stop['lon'], origin_stop['lat'])
        )
        walk_from_stop = self.directions.get_walking_route(
            (dest_stop['lon'], dest_stop['lat']), dest_coords
        )
        
        # Calculate totals
        walk_time = (walk_to_stop.get('duration_min', 5) + 
                     walk_from_stop.get('duration_min', 5))
        bus_time = best_bus.get('estimated_time', 20)
        total_time = walk_time + bus_time
        
        segments = [
            {
                'type': 'walk',
                'from': origin,
                'to': origin_stop['name'],
                'duration_min': walk_to_stop.get('duration_min', 5),
                'distance_m': walk_to_stop.get('distance_m', 500),
                'instruction': f"🚶 Walk to {origin_stop['name']} Bus Stop (~{int(walk_to_stop.get('duration_min', 5))} min)"
            },
            {
                'type': 'bus',
                'route_number': best_bus.get('route_number', 'Local Bus'),
                'from': origin_stop['name'],
                'to': dest_stop['name'],
                'duration_min': bus_time,
                'fare': best_bus.get('fare', 25),
                'instruction': f"🚌 Take Bus {best_bus.get('route_number', '')} towards {destination} (~{bus_time} min)"
            },
            {
                'type': 'walk',
                'from': dest_stop['name'],
                'to': destination,
                'duration_min': walk_from_stop.get('duration_min', 5),
                'distance_m': walk_from_stop.get('distance_m', 500),
                'instruction': f"🚶 Walk to {destination} (~{int(walk_from_stop.get('duration_min', 5))} min)"
            }
        ]
        
        # Generate step-by-step text
        steps_text = self._generate_steps_text(segments, origin, destination, city)
        
        return {
            'mode': 'Bus',
            'segments': segments,
            'total_time': int(total_time),
            'total_cost': best_bus.get('fare', 25),
            'route_number': best_bus.get('route_number', 'Local Bus'),
            'steps_text': steps_text,
            'from_stop': origin_stop['name'],
            'to_stop': dest_stop['name']
        }
    
    def _plan_metro_route(self, origin: str, destination: str, city: str,
                          origin_coords: Tuple, dest_coords: Tuple) -> Optional[Dict]:
        """Plan a route using metro."""
        # Find nearest metro stations
        origin_station = self.transit.find_nearest_stop(
            origin_coords[1], origin_coords[0], city, "metro", max_distance_km=2.0
        )
        dest_station = self.transit.find_nearest_stop(
            dest_coords[1], dest_coords[0], city, "metro", max_distance_km=2.0
        )
        
        if not origin_station or not dest_station:
            return None
        
        # Same station? Not useful
        if origin_station['name'] == dest_station['name']:
            return None
        
        # Find metro route
        metro_routes = self.transit.find_routes_between(
            origin_station['name'], dest_station['name'], city, "metro"
        )
        
        if not metro_routes:
            return None
        
        best_metro = metro_routes[0]
        
        # Get walking segments
        walk_to_station = self.directions.get_walking_route(
            origin_coords, (origin_station['lon'], origin_station['lat'])
        )
        walk_from_station = self.directions.get_walking_route(
            (dest_station['lon'], dest_station['lat']), dest_coords
        )
        
        walk_time = (walk_to_station.get('duration_min', 5) + 
                     walk_from_station.get('duration_min', 5))
        metro_time = best_metro.get('estimated_time', 15)
        total_time = walk_time + metro_time
        
        segments = [
            {
                'type': 'walk',
                'from': origin,
                'to': origin_station['name'],
                'duration_min': walk_to_station.get('duration_min', 5),
                'instruction': f"🚶 Walk to {origin_station['name']} Metro Station (~{int(walk_to_station.get('duration_min', 5))} min)"
            },
            {
                'type': 'metro',
                'line': best_metro.get('line', 'Purple'),
                'from': origin_station['name'],
                'to': dest_station['name'],
                'duration_min': metro_time,
                'fare': best_metro.get('fare', 30),
                'num_stations': best_metro.get('num_stations', 5),
                'instruction': f"🚇 Take {best_metro.get('line_name', 'Metro')} Line to {dest_station['name']} (~{metro_time} min)"
            },
            {
                'type': 'walk',
                'from': dest_station['name'],
                'to': destination,
                'duration_min': walk_from_station.get('duration_min', 5),
                'instruction': f"🚶 Walk to {destination} (~{int(walk_from_station.get('duration_min', 5))} min)"
            }
        ]
        
        steps_text = self._generate_steps_text(segments, origin, destination, city)
        
        return {
            'mode': 'Metro',
            'segments': segments,
            'total_time': int(total_time),
            'total_cost': best_metro.get('fare', 30),
            'line': best_metro.get('line', 'Purple'),
            'steps_text': steps_text,
            'from_station': origin_station['name'],
            'to_station': dest_station['name']
        }
    
    def _walking_only_route(self, origin: str, destination: str,
                            origin_coords: Tuple, dest_coords: Tuple) -> Dict:
        """Plan a walking-only route."""
        walk = self.directions.get_walking_route(origin_coords, dest_coords)
        
        return {
            'mode': 'Walk',
            'segments': [
                {
                    'type': 'walk',
                    'from': origin,
                    'to': destination,
                    'duration_min': walk.get('duration_min', 30),
                    'distance_m': walk.get('distance_m', 2000),
                    'instruction': f"🚶 Walk to {destination} (~{int(walk.get('duration_min', 30))} min)"
                }
            ],
            'total_time': int(walk.get('duration_min', 30)),
            'total_cost': 0,
            'steps_text': f"🚶 Walk from {origin} to {destination}\n⏱️ ~{int(walk.get('duration_min', 30))} minutes | 💰 Free"
        }
    
    def _auto_route(self, origin: str, destination: str,
                    origin_coords: Tuple, dest_coords: Tuple, city: str) -> Dict:
        """Plan an auto/taxi route (estimate)."""
        dist_km = self._haversine(
            origin_coords[1], origin_coords[0],
            dest_coords[1], dest_coords[0]
        )
        
        # Estimate: Auto ₹30 base + ₹15/km, ~25 km/h in city
        fare = int(30 + dist_km * 15)
        time = int((dist_km / 25) * 60) + 5  # +5 min for pickup
        
        return {
            'mode': 'Auto',
            'segments': [
                {
                    'type': 'auto',
                    'from': origin,
                    'to': destination,
                    'duration_min': time,
                    'fare': fare,
                    'instruction': f"🛺 Take auto/cab to {destination} (~{time} min)"
                }
            ],
            'total_time': time,
            'total_cost': fare,
            'steps_text': f"🛺 Book auto/cab from {origin} to {destination}\n⏱️ ~{time} minutes | 💰 ₹{fare}"
        }
    
    def _generate_steps_text(self, segments: List[Dict], origin: str, 
                             destination: str, city: str) -> str:
        """Generate human-readable step-by-step directions."""
        lines = [f"📍 Route from {origin} to {destination}:\n"]
        
        for i, seg in enumerate(segments, 1):
            lines.append(f"{i}. {seg['instruction']}")
        
        # Add next departure time (mock)
        now = datetime.now()
        next_time = now.replace(minute=(now.minute // 5 + 1) * 5 % 60)
        
        total_time = sum(s.get('duration_min', 0) for s in segments)
        total_cost = sum(s.get('fare', 0) for s in segments)
        
        lines.append(f"\n🕐 Next departure: {next_time.strftime('%H:%M')}")
        lines.append(f"⏱️ Total: ~{int(total_time)} mins | 💰 ₹{total_cost}")
        
        return "\n".join(lines)
    
    def _basic_route(self, origin: str, destination: str, 
                     city: str, mode: str) -> Dict:
        """Fallback basic route when coordinates unavailable."""
        return {
            'mode': mode.capitalize() if mode != 'auto' else 'Transit',
            'segments': [],
            'total_time': 30,
            'total_cost': 25,
            'steps_text': f"📍 From {origin} to {destination}\n• Check local transit options\n• Estimated: ~30 mins, ₹25"
        }
    
    def _get_coordinates(self, location: str, city: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for a location."""
        # First try transit stops/stations
        stop = self.transit.find_stop(location, city)
        if stop:
            return (stop['lon'], stop['lat'])
        
        # Try geocoding
        return self.geocoder.geocode(location, city)
    
    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c


# Global instance
_router: Optional[HybridRouter] = None


def get_hybrid_router() -> HybridRouter:
    """Get or create global HybridRouter instance."""
    global _router
    if _router is None:
        _router = HybridRouter()
    return _router


if __name__ == "__main__":
    # Test the router
    print("=== Testing HybridRouter ===")
    
    router = get_hybrid_router()
    
    # Test Bengaluru bus route
    print("\n--- Hebbal to Majestic ---")
    route = router.plan_route("Hebbal", "Majestic", "bengaluru")
    print(f"Mode: {route.get('mode')}")
    print(f"Time: {route.get('total_time')} min")
    print(f"Cost: ₹{route.get('total_cost')}")
    print(f"\nSteps:\n{route.get('steps_text')}")
    
    # Test Bengaluru metro route
    print("\n--- Indiranagar to MG Road ---")
    route = router.plan_route("Indiranagar", "MG Road", "bengaluru", "metro")
    print(f"Mode: {route.get('mode')}")
    print(f"Time: {route.get('total_time')} min")
    print(f"Cost: ₹{route.get('total_cost')}")
    print(f"\nSteps:\n{route.get('steps_text')}")
