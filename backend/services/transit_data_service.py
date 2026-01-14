"""
Unified Transit Data Service for Bengaluru and Mumbai.
Loads and provides access to bus, metro, and suburban rail data.
"""

import csv
import json
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from math import radians, sin, cos, sqrt, atan2

from services.kml_parser import parse_kml_stops


class TransitDataService:
    """
    Unified service for loading and querying transit data.
    Supports: BMTC (Bangalore buses), Namma Metro, Mumbai BEST, Mumbai Suburban.
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / "data"
        
        # Data stores by city and mode
        self.data: Dict[str, Dict[str, List[Dict]]] = {
            "bengaluru": {
                "bus": [],
                "metro": []
            },
            "mumbai": {
                "bus": [],
                "metro": [],
                "suburban": []
            }
        }
        
        # Indexes for fast lookup
        self._stop_index: Dict[str, Dict] = {}  # name.lower() -> stop data
        self._route_index: Dict[str, List[str]] = {}  # route_number -> [stop_names]
        
        self._loaded = False
    
    def load_all(self) -> None:
        """Load all transit data for both cities."""
        if self._loaded:
            return
            
        self._load_bengaluru_data()
        self._load_mumbai_data()
        self._build_indexes()
        self._loaded = True
        print(f"[TransitDataService] Loaded: Bengaluru ({len(self.data['bengaluru']['bus'])} bus stops, "
              f"{len(self.data['bengaluru']['metro'])} metro stations), "
              f"Mumbai ({len(self.data['mumbai']['bus'])} bus stops, "
              f"{len(self.data['mumbai']['suburban'])} suburban stations)")
    
    def _load_bengaluru_data(self) -> None:
        """Load Bengaluru BMTC and Namma Metro data."""
        # Load BMTC bus stops from CSV
        bmtc_path = self.data_dir / "bengaluru" / "bmtc_stops.csv"
        if bmtc_path.exists():
            self.data["bengaluru"]["bus"] = self._parse_bmtc_csv(bmtc_path)
        else:
            print(f"[TransitDataService] BMTC CSV not found: {bmtc_path}")
        
        # Load Namma Metro stations from JSON
        metro_path = self.data_dir / "bengaluru" / "metro_stations.json"
        if metro_path.exists():
            self.data["bengaluru"]["metro"] = self._parse_metro_json(metro_path)
        else:
            print(f"[TransitDataService] Metro JSON not found: {metro_path}")
    
    def _load_mumbai_data(self) -> None:
        """Load Mumbai BEST and Suburban data."""
        # Load BEST bus stops from KML
        best_path = self.data_dir / "mumbai" / "best_stops.kml"
        if best_path.exists():
            self.data["mumbai"]["bus"] = parse_kml_stops(str(best_path))
        else:
            print(f"[TransitDataService] BEST KML not found: {best_path}")
        
        # Load Suburban stations from KML
        suburban_path = self.data_dir / "mumbai" / "suburban_stations.kml"
        if suburban_path.exists():
            self.data["mumbai"]["suburban"] = parse_kml_stops(str(suburban_path))
        else:
            print(f"[TransitDataService] Suburban KML not found: {suburban_path}")
    
    def _parse_bmtc_csv(self, path: Path) -> List[Dict]:
        """Parse BMTC CSV from OpenCity.in"""
        stops = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # Parse routes dictionary string
                        routes_str = row.get('Routes with num trips', '{}')
                        routes_dict = ast.literal_eval(routes_str) if routes_str else {}
                        routes = list(routes_dict.keys())
                        
                        stop = {
                            'name': row.get('Stop Name', '').strip(),
                            'lat': float(row.get('Latitude', 0)),
                            'lon': float(row.get('Longitude', 0)),
                            'routes': routes,
                            'trips': int(row.get('Num trips in stop', 0)),
                            'city': 'bengaluru',
                            'mode': 'bus'
                        }
                        if stop['name'] and stop['lat'] and stop['lon']:
                            stops.append(stop)
                    except (ValueError, SyntaxError) as e:
                        continue  # Skip malformed rows
        except Exception as e:
            print(f"[TransitDataService] Error parsing BMTC CSV: {e}")
        return stops
    
    def _parse_metro_json(self, path: Path) -> List[Dict]:
        """Parse Namma Metro JSON data."""
        stations = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            fares = data.get('fares', {})
            
            for line_code, line_data in data.get('lines', {}).items():
                line_name = line_data.get('name', line_code)
                color = line_data.get('color', '#888888')
                
                for idx, station in enumerate(line_data.get('stations', [])):
                    stations.append({
                        'name': station.get('name', ''),
                        'lat': station.get('lat', 0),
                        'lon': station.get('lon', 0),
                        'line': line_code,
                        'line_name': line_name,
                        'color': color,
                        'interchange': station.get('interchange', []),
                        'station_index': idx,
                        'city': 'bengaluru',
                        'mode': 'metro',
                        'fares': fares
                    })
        except Exception as e:
            print(f"[TransitDataService] Error parsing Metro JSON: {e}")
        return stations
    
    def _build_indexes(self) -> None:
        """Build lookup indexes for fast search."""
        for city, modes in self.data.items():
            for mode, stops in modes.items():
                for stop in stops:
                    key = f"{city}:{stop['name'].lower()}"
                    self._stop_index[key] = stop
                    
                    # Index routes
                    for route in stop.get('routes', []):
                        route_key = f"{city}:{route}"
                        if route_key not in self._route_index:
                            self._route_index[route_key] = []
                        self._route_index[route_key].append(stop['name'])
    
    # Bengaluru location aliases - map common names to coordinates/BMTC stop names
    BENGALURU_ALIASES = {
        # Major bus stations
        "majestic": {"lat": 12.9764, "lon": 77.5707, "keywords": ["kempegowda", "kbs", "city railway"]},
        "kempegowda bus station": {"lat": 12.9764, "lon": 77.5707, "keywords": ["majestic"]},
        
        # North Bengaluru
        "hebbal": {"lat": 13.0358, "lon": 77.5970, "keywords": ["esteem mall", "hebbala", "hebbal flyover"]},
        "yeshwanthpur": {"lat": 13.0227, "lon": 77.5505, "keywords": ["yeshwantpur", "yeswanthpur"]},
        "yelahanka": {"lat": 13.1007, "lon": 77.5963, "keywords": ["yelahanka new town"]},
        
        # South Bengaluru
        "jayanagar": {"lat": 12.9308, "lon": 77.5838, "keywords": ["jayanagar 4th block", "cool joint"]},
        "banashankari": {"lat": 12.9255, "lon": 77.5468, "keywords": ["bsk", "banashankari bus station"]},
        "jp nagar": {"lat": 12.9063, "lon": 77.5857, "keywords": ["jpnagar", "jp nagar 6th phase"]},
        "btm layout": {"lat": 12.9166, "lon": 77.6101, "keywords": ["btm", "btm 2nd stage"]},
        
        # East Bengaluru
        "koramangala": {"lat": 12.9352, "lon": 77.6245, "keywords": ["forum mall", "koramangala 4th block"]},
        "indiranagar": {"lat": 12.9719, "lon": 77.6412, "keywords": ["100 feet road", "esi hospital"]},
        "whitefield": {"lat": 12.9698, "lon": 77.7500, "keywords": ["itpl", "hope farm"]},
        "kr puram": {"lat": 13.0072, "lon": 77.6820, "keywords": ["krishnarajapuram", "tin factory"]},
        "marathahalli": {"lat": 12.9591, "lon": 77.7011, "keywords": ["marthahalli", "outer ring road"]},
        
        # Central
        "mg road": {"lat": 12.9753, "lon": 77.6068, "keywords": ["brigade road", "trinity"]},
        "shivajinagar": {"lat": 12.9850, "lon": 77.6053, "keywords": ["russell market"]},
        "vijayanagar": {"lat": 12.9711, "lon": 77.5361, "keywords": ["rpc layout"]},
        
        # Tech areas
        "electronic city": {"lat": 12.8399, "lon": 77.6770, "keywords": ["infosys", "wipro"]},
        "silk board": {"lat": 12.9177, "lon": 77.6238, "keywords": ["silkboard junction"]},
        "manyata tech park": {"lat": 13.0474, "lon": 77.6218, "keywords": ["manyata", "nagawara"]},
        
        # Colleges/Universities
        "rvce": {"lat": 12.9237, "lon": 77.4987, "keywords": ["rv college", "rashtreeya vidyalaya"]},
    }
    
    def find_stop(self, name: str, city: str = "bengaluru", mode: str = None) -> Optional[Dict]:
        """Find a stop by name, using aliases and coordinate fallback."""
        name_lower = name.lower().strip()
        
        # 1. Try exact match first
        key = f"{city}:{name_lower}"
        stop = self._stop_index.get(key)
        if stop and (mode is None or stop.get('mode') == mode):
            return stop
        
        # 2. Try alias lookup for Bengaluru
        if city == "bengaluru" and name_lower in self.BENGALURU_ALIASES:
            alias_info = self.BENGALURU_ALIASES[name_lower]
            # Find nearest stop to alias coordinates
            return self.find_nearest_stop(
                alias_info["lat"], alias_info["lon"], 
                city, mode, max_distance_km=1.0
            )
        
        # 3. Try alias keywords
        for alias_name, alias_info in self.BENGALURU_ALIASES.items():
            if name_lower in alias_info.get("keywords", []) or alias_name in name_lower:
                return self.find_nearest_stop(
                    alias_info["lat"], alias_info["lon"],
                    city, mode, max_distance_km=1.0
                )
        
        # 4. Fuzzy substring match
        for k, v in self._stop_index.items():
            if k.startswith(f"{city}:") and name_lower in k:
                if mode is None or v.get('mode') == mode:
                    return v
        
        # 5. Reverse fuzzy match (stop name contains query)
        for k, v in self._stop_index.items():
            if k.startswith(f"{city}:"):
                stop_name_lower = k.split(":", 1)[1]
                if name_lower in stop_name_lower or stop_name_lower in name_lower:
                    if mode is None or v.get('mode') == mode:
                        return v
        
        return None
    
    def find_nearest_stop(self, lat: float, lon: float, city: str = "bengaluru", 
                          mode: str = None, max_distance_km: float = 2.0) -> Optional[Dict]:
        """Find nearest stop to given coordinates."""
        nearest = None
        min_dist = float('inf')
        
        for city_key, modes in self.data.items():
            if city_key != city:
                continue
            for mode_key, stops in modes.items():
                if mode and mode_key != mode:
                    continue
                for stop in stops:
                    dist = self._haversine(lat, lon, stop['lat'], stop['lon'])
                    if dist < min_dist and dist <= max_distance_km:
                        min_dist = dist
                        nearest = {**stop, 'distance_km': round(dist, 2)}
        
        return nearest
    
    def find_routes_between(self, origin: str, destination: str, city: str = "bengaluru",
                            mode: str = "bus") -> List[Dict]:
        """
        Find routes/lines connecting two stops.
        Returns list of route options with details.
        """
        routes = []
        
        origin_stop = self.find_stop(origin, city, mode)
        dest_stop = self.find_stop(destination, city, mode)
        
        if not origin_stop or not dest_stop:
            # Try nearest stops
            return routes
        
        if mode == "bus":
            routes = self._find_bus_routes(origin_stop, dest_stop, city)
        elif mode == "metro":
            routes = self._find_metro_routes(origin_stop, dest_stop, city)
        
        return routes
    
    def _find_bus_routes(self, origin: Dict, dest: Dict, city: str) -> List[Dict]:
        """Find bus routes connecting two stops/areas."""
        routes = []
        
        # Collect routes from multiple stops near origin (1km radius)
        origin_routes = set(origin.get('routes', []))
        origin_area_stops = self._find_stops_in_radius(
            origin['lat'], origin['lon'], city, "bus", radius_km=1.0
        )
        for stop in origin_area_stops:
            origin_routes.update(stop.get('routes', []))
        
        # Collect routes from multiple stops near destination (1km radius)
        dest_routes = set(dest.get('routes', []))
        dest_area_stops = self._find_stops_in_radius(
            dest['lat'], dest['lon'], city, "bus", radius_km=1.0
        )
        for stop in dest_area_stops:
            dest_routes.update(stop.get('routes', []))
        
        # Find common routes (buses that serve both areas)
        common = origin_routes & dest_routes
        
        # Filter to readable route numbers (not too long/complex)
        common = [r for r in common if len(r) <= 12 and '-' in r or r.isalnum()]
        
        for route_num in sorted(common)[:5]:  # Top 5 routes
            routes.append({
                'type': 'direct',
                'route_number': route_num,
                'from_stop': origin['name'],
                'to_stop': dest['name'],
                'transfers': 0,
                'estimated_time': self._estimate_bus_time(origin, dest),
                'fare': self._estimate_bus_fare(origin, dest),
                'city': city
            })
        
        # If still no routes, try broader search (2km radius)
        if not routes:
            origin_routes_broad = set()
            for stop in self._find_stops_in_radius(origin['lat'], origin['lon'], city, "bus", 2.0):
                origin_routes_broad.update(stop.get('routes', []))
            
            dest_routes_broad = set()
            for stop in self._find_stops_in_radius(dest['lat'], dest['lon'], city, "bus", 2.0):
                dest_routes_broad.update(stop.get('routes', []))
            
            common_broad = origin_routes_broad & dest_routes_broad
            common_broad = [r for r in common_broad if len(r) <= 12]
            
            for route_num in sorted(common_broad)[:3]:
                routes.append({
                    'type': 'direct',
                    'route_number': route_num,
                    'from_stop': origin['name'],
                    'to_stop': dest['name'],
                    'transfers': 0,
                    'estimated_time': self._estimate_bus_time(origin, dest),
                    'fare': self._estimate_bus_fare(origin, dest),
                    'city': city
                })
        
        return sorted(routes, key=lambda x: x.get('estimated_time', 999))[:5]
    
    def _find_stops_in_radius(self, lat: float, lon: float, city: str, 
                               mode: str = "bus", radius_km: float = 1.0) -> List[Dict]:
        """Find all stops within a radius of given coordinates."""
        stops = []
        
        if city not in self.data or mode not in self.data[city]:
            return stops
        
        for stop in self.data[city][mode]:
            dist = self._haversine(lat, lon, stop['lat'], stop['lon'])
            if dist <= radius_km:
                stops.append(stop)
        
        return stops
    
    def _find_metro_routes(self, origin: Dict, dest: Dict, city: str) -> List[Dict]:
        """Find metro route between two stations."""
        routes = []
        
        origin_line = origin.get('line')
        dest_line = dest.get('line')
        
        if origin_line == dest_line:
            # Same line - direct route
            num_stations = abs(origin.get('station_index', 0) - dest.get('station_index', 0))
            time = num_stations * 2 + 5  # ~2 min per station + boarding
            fare = self._calculate_metro_fare(num_stations, origin.get('fares', {}))
            
            routes.append({
                'type': 'direct',
                'line': origin_line,
                'line_name': origin.get('line_name'),
                'from_station': origin['name'],
                'to_station': dest['name'],
                'num_stations': num_stations,
                'transfers': 0,
                'estimated_time': time,
                'fare': fare,
                'city': city
            })
        else:
            # Need transfer at Majestic (interchange)
            # Simplified: assume transfer at Majestic for Purple-Green interchange
            routes.append({
                'type': 'transfer',
                'from_station': origin['name'],
                'to_station': dest['name'],
                'via': 'Majestic',
                'lines': [origin_line, dest_line],
                'transfers': 1,
                'estimated_time': 30,  # Approximate
                'fare': 35,  # Approximate combined fare
                'city': city
            })
        
        return routes
    
    def _calculate_metro_fare(self, num_stations: int, fares: Dict) -> int:
        """Calculate metro fare based on number of stations."""
        base = fares.get('base_fare', 10)
        per_station = fares.get('per_station', 2)
        max_fare = fares.get('max_fare', 60)
        return min(base + (num_stations * per_station), max_fare)
    
    def _estimate_bus_time(self, origin: Dict, dest: Dict) -> int:
        """Estimate bus travel time in minutes."""
        dist = self._haversine(origin['lat'], origin['lon'], dest['lat'], dest['lon'])
        # Assume average speed of 15 km/h in city traffic + waiting
        return int((dist / 15) * 60) + 10  # + 10 min for waiting
    
    def _estimate_bus_fare(self, origin: Dict, dest: Dict) -> int:
        """Estimate bus fare in rupees."""
        dist = self._haversine(origin['lat'], origin['lon'], dest['lat'], dest['lon'])
        # BMTC fare: ~₹5 base + ₹1.5/km
        return max(5, int(5 + dist * 1.5))
    
    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km."""
        R = 6371  # Earth's radius in km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def get_city_from_location(self, location: str) -> str:
        """Detect city from location name."""
        location_lower = location.lower()
        
        # Mumbai landmarks
        mumbai_keywords = [
            'dadar', 'andheri', 'bandra', 'kurla', 'thane', 'borivali',
            'churchgate', 'cst', 'mumbai', 'malad', 'goregaon', 'kandivali',
            'vashi', 'panvel', 'navi mumbai', 'worli', 'lower parel'
        ]
        
        for keyword in mumbai_keywords:
            if keyword in location_lower:
                return 'mumbai'
        
        # Default to Bengaluru
        return 'bengaluru'
    
    def get_all_stops(self, city: str, mode: str = None) -> List[Dict]:
        """Get all stops for a city and optionally filter by mode."""
        if city not in self.data:
            return []
        
        if mode:
            return self.data[city].get(mode, [])
        
        all_stops = []
        for stops in self.data[city].values():
            all_stops.extend(stops)
        return all_stops


# Global instance
_transit_service: Optional[TransitDataService] = None


def get_transit_service() -> TransitDataService:
    """Get or create the global transit service instance."""
    global _transit_service
    if _transit_service is None:
        _transit_service = TransitDataService()
        _transit_service.load_all()
    return _transit_service


if __name__ == "__main__":
    # Test the service
    service = get_transit_service()
    
    print("\n=== Testing TransitDataService ===")
    
    # Test Bengaluru bus stop lookup
    stop = service.find_stop("Hebbal", "bengaluru", "bus")
    print(f"\nHebbal bus stop: {stop}")
    
    # Test Bengaluru metro
    mg_road = service.find_stop("MG Road", "bengaluru", "metro")
    print(f"\nMG Road metro: {mg_road}")
    
    # Test routes between
    routes = service.find_routes_between("Indiranagar", "MG Road", "bengaluru", "metro")
    print(f"\nIndiranagar to MG Road metro routes: {routes}")
    
    # Test city detection
    city = service.get_city_from_location("Dadar to Andheri")
    print(f"\nDetected city for 'Dadar to Andheri': {city}")
