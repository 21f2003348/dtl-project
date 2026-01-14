"""
Mapbox Directions API wrapper for walking directions.
Uses the mapbox/walking profile to get pedestrian routes.
"""

import os
import requests
from typing import Dict, List, Optional, Tuple
from functools import lru_cache


class MapboxDirections:
    """
    Wrapper for Mapbox Directions API.
    Provides walking directions between two points.
    """
    
    BASE_URL = "https://api.mapbox.com/directions/v5/mapbox/walking"
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("TOKEN")
        if not self.access_token:
            print("[MapboxDirections] Warning: No TOKEN found in environment")
    
    def get_walking_route(self, origin: Tuple[float, float], 
                          destination: Tuple[float, float],
                          steps: bool = True) -> Dict:
        """
        Get walking directions between two coordinate pairs.
        
        Args:
            origin: (longitude, latitude) tuple
            destination: (longitude, latitude) tuple
            steps: Whether to include turn-by-turn steps
            
        Returns:
            Dict with distance_m, duration_sec, geometry, steps
        """
        if not self.access_token:
            return self._fallback_estimate(origin, destination)
        
        try:
            # Format coordinates as lon,lat;lon,lat
            coords = f"{origin[0]},{origin[1]};{destination[0]},{destination[1]}"
            
            params = {
                "access_token": self.access_token,
                "geometries": "geojson",
                "steps": str(steps).lower(),
                "overview": "full",
                "language": "en"
            }
            
            url = f"{self.BASE_URL}/{coords}"
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_response(data)
            else:
                print(f"[MapboxDirections] API error: {response.status_code}")
                return self._fallback_estimate(origin, destination)
                
        except requests.RequestException as e:
            print(f"[MapboxDirections] Request error: {e}")
            return self._fallback_estimate(origin, destination)
    
    def _parse_response(self, data: Dict) -> Dict:
        """Parse Mapbox API response."""
        if not data.get("routes"):
            return {"error": "No routes found"}
        
        route = data["routes"][0]
        legs = route.get("legs", [{}])
        leg = legs[0] if legs else {}
        
        # Extract steps
        steps = []
        for step in leg.get("steps", []):
            maneuver = step.get("maneuver", {})
            steps.append({
                "instruction": maneuver.get("instruction", ""),
                "type": maneuver.get("type", ""),
                "modifier": maneuver.get("modifier", ""),
                "distance_m": step.get("distance", 0),
                "duration_sec": step.get("duration", 0),
                "name": step.get("name", "")
            })
        
        return {
            "distance_m": route.get("distance", 0),
            "duration_sec": route.get("duration", 0),
            "duration_min": round(route.get("duration", 0) / 60, 1),
            "geometry": route.get("geometry", {}),
            "steps": steps,
            "source": "mapbox"
        }
    
    def _fallback_estimate(self, origin: Tuple[float, float], 
                           destination: Tuple[float, float]) -> Dict:
        """Fallback estimate when API is unavailable."""
        # Calculate straight-line distance
        dist_km = self._haversine(origin[1], origin[0], destination[1], destination[0])
        
        # Assume walking speed of 5 km/h, add 30% for non-straight paths
        walking_dist_km = dist_km * 1.3
        duration_min = (walking_dist_km / 5) * 60
        
        return {
            "distance_m": int(walking_dist_km * 1000),
            "duration_sec": int(duration_min * 60),
            "duration_min": round(duration_min, 1),
            "geometry": None,
            "steps": [
                {
                    "instruction": f"Walk {round(walking_dist_km * 1000)}m to destination",
                    "type": "walk",
                    "distance_m": int(walking_dist_km * 1000),
                    "duration_sec": int(duration_min * 60)
                }
            ],
            "source": "estimate"
        }
    
    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth's radius in km
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def get_walking_time_text(self, duration_min: float) -> str:
        """Format walking time as human-readable text."""
        if duration_min < 1:
            return "less than a minute"
        elif duration_min < 2:
            return "about 1 minute"
        else:
            return f"about {int(duration_min)} minutes"


# Geocoding helper using Mapbox
class MapboxGeocoder:
    """
    Simple geocoder using Mapbox Geocoding API.
    Converts place names to coordinates.
    """
    
    BASE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("TOKEN")
    
    @lru_cache(maxsize=100)
    def geocode(self, place_name: str, city: str = "Bengaluru") -> Optional[Tuple[float, float]]:
        """
        Geocode a place name to coordinates.
        
        Args:
            place_name: Name of the place
            city: City context for better results
            
        Returns:
            (longitude, latitude) tuple or None if not found
        """
        if not self.access_token:
            return None
        
        try:
            query = f"{place_name}, {city}, India"
            params = {
                "access_token": self.access_token,
                "limit": 1,
                "country": "IN"
            }
            
            url = f"{self.BASE_URL}/{requests.utils.quote(query)}.json"
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                features = data.get("features", [])
                if features:
                    coords = features[0].get("center", [])
                    if len(coords) == 2:
                        return (coords[0], coords[1])  # lon, lat
            
        except requests.RequestException as e:
            print(f"[MapboxGeocoder] Error: {e}")
        
        return None


# Global instances
_directions: Optional[MapboxDirections] = None
_geocoder: Optional[MapboxGeocoder] = None


def get_mapbox_directions() -> MapboxDirections:
    """Get or create global MapboxDirections instance."""
    global _directions
    if _directions is None:
        _directions = MapboxDirections()
    return _directions


def get_mapbox_geocoder() -> MapboxGeocoder:
    """Get or create global MapboxGeocoder instance."""
    global _geocoder
    if _geocoder is None:
        _geocoder = MapboxGeocoder()
    return _geocoder


if __name__ == "__main__":
    # Test the service
    print("=== Testing MapboxDirections ===")
    
    directions = get_mapbox_directions()
    
    # Test walking route (Hebbal to Majestic area coordinates)
    origin = (77.5891, 13.0358)  # Hebbal (lon, lat)
    dest = (77.5707, 12.9764)    # Majestic (lon, lat)
    
    result = directions.get_walking_route(origin, dest)
    print(f"\nHebbal to Majestic walking:")
    print(f"  Distance: {result.get('distance_m')}m")
    print(f"  Duration: {result.get('duration_min')} minutes")
    print(f"  Source: {result.get('source')}")
    
    # Test geocoding
    geocoder = get_mapbox_geocoder()
    coords = geocoder.geocode("Hebbal", "Bengaluru")
    print(f"\nGeocoded 'Hebbal': {coords}")
