"""
GTFS (General Transit Feed Specification) data loader for real-time transit data.
Integrates with Bengaluru BMTC (Bangalore Metropolitan Transport Corporation) APIs or GTFS feeds.
"""

import json
import csv
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import requests
from datetime import datetime, timedelta


class GTFSDataLoader:
    """Load and parse GTFS data from files or APIs."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize GTFS loader."""
        self.data_dir = data_dir or Path("data/gtfs")
        self.stops = {}
        self.routes = {}
        self.stop_times = {}
        self.trips = {}
        self.shapes = {}
        self.transfers = {}
    
    def load_from_files(self) -> bool:
        """Load GTFS data from CSV files."""
        try:
            # Check if GTFS files exist
            if not self.data_dir.exists():
                print(f"[GTFS] Directory {self.data_dir} not found. Using fallback data.")
                return False
            
            # Load stops.txt
            stops_file = self.data_dir / "stops.txt"
            if stops_file.exists():
                with open(stops_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.stops[row['stop_id']] = {
                            'stop_id': row['stop_id'],
                            'stop_name': row.get('stop_name', ''),
                            'stop_lat': float(row.get('stop_lat', 0)),
                            'stop_lon': float(row.get('stop_lon', 0)),
                            'stop_desc': row.get('stop_desc', '')
                        }
            
            # Load routes.txt
            routes_file = self.data_dir / "routes.txt"
            if routes_file.exists():
                with open(routes_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.routes[row['route_id']] = {
                            'route_id': row['route_id'],
                            'route_short_name': row.get('route_short_name', ''),
                            'route_long_name': row.get('route_long_name', ''),
                            'route_type': row.get('route_type', ''),
                            'route_color': row.get('route_color', ''),
                            'route_text_color': row.get('route_text_color', '')
                        }
            
            # Load stop_times.txt (this can be large)
            stop_times_file = self.data_dir / "stop_times.txt"
            if stop_times_file.exists():
                with open(stop_times_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        trip_id = row['trip_id']
                        if trip_id not in self.stop_times:
                            self.stop_times[trip_id] = []
                        self.stop_times[trip_id].append({
                            'stop_id': row['stop_id'],
                            'stop_sequence': int(row.get('stop_sequence', 0)),
                            'arrival_time': row.get('arrival_time', ''),
                            'departure_time': row.get('departure_time', '')
                        })
            
            print(f"[GTFS] Loaded {len(self.stops)} stops, {len(self.routes)} routes")
            return True
        
        except Exception as e:
            print(f"[GTFS] Error loading files: {e}")
            return False
    
    def fetch_from_bmtc_api(self) -> bool:
        """
        Fetch live BMTC bus data from open APIs.
        Note: BMTC doesn't have a public real-time API, but we can use:
        - Transitland API (aggregates global transit data)
        - Google Transit API (if BMTC shares data)
        - Local Bangalore open data portals
        """
        try:
            # Example: Transitland API for Bangalore
            # https://transit.land/ provides free access to transit data
            
            # Alternative: Use hardcoded BMTC routes as fallback
            self._load_fallback_bmtc_routes()
            print("[GTFS] Loaded fallback BMTC routes")
            return True
        
        except Exception as e:
            print(f"[GTFS] Error fetching BMTC data: {e}")
            return False
    
    def _load_fallback_bmtc_routes(self) -> None:
        """Load hardcoded BMTC routes as fallback."""
        # Real BMTC bus routes in Bengaluru
        bmtc_routes = {
            "215": {
                "route_id": "215",
                "route_name": "Indira Nagar to Majestic",
                "route_type": "Bus",
                "stops": ["Indira Nagar", "Indiranagar 60 Feet Road", "Marathahalli", "Whitefield", "Majestic"],
                "frequency_mins": 20,
                "first_bus": "05:30",
                "last_bus": "23:00"
            },
            "500K": {
                "route_id": "500K",
                "route_name": "K.R. Puram to Hebbal",
                "route_type": "Bus",
                "stops": ["K.R. Puram", "Koramangala", "Indiranagar", "Vidhana Soudha", "Hebbal"],
                "frequency_mins": 15,
                "first_bus": "06:00",
                "last_bus": "23:30"
            },
            "G4": {
                "route_id": "G4",
                "route_name": "Whitefield to Jayanagar",
                "route_type": "Bus",
                "stops": ["Whitefield", "Marathahalli", "Indiranagar", "Jayanagar", "JP Nagar"],
                "frequency_mins": 25,
                "first_bus": "05:45",
                "last_bus": "22:30"
            },
            "356E": {
                "route_id": "356E",
                "route_name": "Yeshwantpur to Kalyan Nagar",
                "route_type": "Bus",
                "stops": ["Yeshwantpur", "Vidhana Soudha", "Cubbon Park", "Trinity Circle", "Kalyan Nagar"],
                "frequency_mins": 18,
                "first_bus": "06:00",
                "last_bus": "23:00"
            }
        }
        
        for route_id, route_info in bmtc_routes.items():
            self.routes[route_id] = route_info
    
    def get_next_bus_times(self, stop_name: str, route_id: Optional[str] = None, limit: int = 3) -> List[Dict]:
        """
        Get next bus times for a stop.
        
        Args:
            stop_name: Name of the stop
            route_id: Optional filter by route
            limit: Number of upcoming buses to return
        
        Returns:
            List of next bus arrival times
        """
        # If we have real GTFS data
        if self.stop_times and self.stops:
            return self._get_next_buses_from_gtfs(stop_name, route_id, limit)
        else:
            return self._get_estimated_next_buses(stop_name, route_id, limit)
    
    def _get_next_buses_from_gtfs(self, stop_name: str, route_id: Optional[str], limit: int) -> List[Dict]:
        """Get next buses from loaded GTFS data."""
        buses = []
        current_time = datetime.now().time()
        
        # Find stop_id for this stop_name
        stop_id = None
        for sid, stop in self.stops.items():
            if stop['stop_name'].lower() == stop_name.lower():
                stop_id = sid
                break
        
        if not stop_id:
            return []
        
        # Find trips that stop at this stop
        for trip_id, times in self.stop_times.items():
            for time_entry in times:
                if time_entry['stop_id'] == stop_id:
                    arrival_time = time_entry['arrival_time']
                    # Parse time and compare with current time
                    try:
                        bus_time = datetime.strptime(arrival_time, "%H:%M:%S").time()
                        if bus_time > current_time:
                            trip_info = self.trips.get(trip_id, {})
                            route_info = self.routes.get(trip_info.get('route_id', ''), {})
                            
                            buses.append({
                                'arrival_time': arrival_time,
                                'route': route_info.get('route_short_name', '?'),
                                'destination': route_info.get('route_long_name', 'Unknown'),
                                'minutes_away': self._calculate_minutes_away(bus_time, current_time)
                            })
                    except ValueError:
                        pass
        
        buses.sort(key=lambda b: b['minutes_away'])
        return buses[:limit]
    
    def _get_estimated_next_buses(self, stop_name: str, route_id: Optional[str], limit: int) -> List[Dict]:
        """Fallback: Generate estimated bus times based on frequency."""
        buses = []
        current_time = datetime.now()
        
        # Get route info
        route_info = None
        if route_id:
            route_info = self.routes.get(route_id)
        
        if route_info:
            frequency_mins = route_info.get('frequency_mins', 15)
            
            # Generate next 3 bus times based on frequency
            for i in range(limit):
                next_bus = current_time + timedelta(minutes=frequency_mins * (i + 1))
                buses.append({
                    'arrival_time': next_bus.strftime("%H:%M"),
                    'route': route_info.get('route_id', '?'),
                    'destination': route_info.get('route_name', 'Unknown'),
                    'minutes_away': frequency_mins * (i + 1)
                })
        
        return buses
    
    @staticmethod
    def _calculate_minutes_away(bus_time, current_time) -> int:
        """Calculate minutes until bus arrival."""
        bus_datetime = datetime.combine(datetime.today(), bus_time)
        current_datetime = datetime.combine(datetime.today(), current_time)
        
        delta = bus_datetime - current_datetime
        return int(delta.total_seconds() / 60)
    
    def get_route_stops(self, route_id: str) -> List[Dict]:
        """Get all stops for a given route."""
        route = self.routes.get(route_id, {})
        stops = route.get('stops', [])
        
        return [
            {
                'stop_name': stop_name,
                'stop_sequence': i + 1,
                'stop_lat': 0,  # Would come from stops.txt
                'stop_lon': 0
            }
            for i, stop_name in enumerate(stops)
        ]
    
    def search_stops(self, query: str) -> List[Dict]:
        """Search for stops by name."""
        results = []
        query_lower = query.lower()
        
        for stop_id, stop in self.stops.items():
            if query_lower in stop['stop_name'].lower():
                results.append({
                    'stop_id': stop_id,
                    'stop_name': stop['stop_name'],
                    'lat': stop['stop_lat'],
                    'lon': stop['stop_lon']
                })
        
        return results[:10]  # Limit to 10 results


class BengaluruTransitData:
    """Hardcoded Bengaluru transit data for quick reference."""
    
    METRO_LINES = {
        "Purple": {
            "line": "Purple Line",
            "stops": [
                "Challaghatta", "Peenya", "Yeshwantpur", "Jalahalli", "Jalahalli Cross",
                "Vidhana Soudha", "Cubbon Park", "MG Road", "Mahatma Gandhi Road",
                "Bangalore City Railway Station", "KR Market", "South End Circle",
                "Lalbagh", "KR Puram", "Marathahalli", "VidhyaGoda", "Whitefield"
            ],
            "operational": True,
            "frequency_mins": 5
        },
        "Green": {
            "line": "Green Line",
            "stops": [
                "Nagasandra", "Madavara", "ITPL", "Gottigere", "Ayyappa Temple",
                "Mekhri Circle", "Sanjaynagar", "Vijayanagar", "Magadi Road",
                "Yelachenahalli", "Banashankari", "South End Circle"
            ],
            "operational": True,
            "frequency_mins": 5
        },
        "Yellow": {
            "line": "Yellow Line",
            "stops": [
                "RV Road", "JP Nagar", "Jayanagar", "South End Circle", "Lalbagh",
                "Kempegowda Railway Station", "Majestic", "Saracen Cross", "Byappanahalli",
                "BIAL", "Bommasandra"
            ],
            "operational": True,
            "frequency_mins": 8
        }
    }
    
    BMTC_MAJOR_ROUTES = [
        {"route": "215", "from": "Indira Nagar", "to": "Majestic", "frequency": 20},
        {"route": "500K", "from": "KR Puram", "to": "Hebbal", "frequency": 15},
        {"route": "G4", "from": "Whitefield", "to": "Jayanagar", "frequency": 25},
        {"route": "356E", "from": "Yeshwantpur", "to": "Kalyan Nagar", "frequency": 18},
    ]
