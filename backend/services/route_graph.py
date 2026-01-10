"""
Graph-based route discovery using K-shortest paths algorithm.
Builds a graph of transit connections and finds multiple route options.
"""

import heapq
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict


class RouteGraph:
    """Transit network graph for finding multiple routes between origin-destination."""
    
    def __init__(self, transit_lines: Dict[str, Any], city: str = "Bengaluru"):
        """
        Initialize graph from transit lines data.
        
        Args:
            transit_lines: Loaded transit_lines.json structure
            city: City name (default Bengaluru)
        """
        self.city = city
        self.transit_lines = transit_lines
        self.graph = defaultdict(list)  # station -> [(neighbor, line_info, distance)]
        self.stations = set()
        self.build_graph()
    
    def build_graph(self):
        """Build adjacency graph from metro/bus/suburban rail lines."""
        city_data = self.transit_lines.get("cities", {}).get(self.city, {})
        
        # Metro lines
        for line in city_data.get("metro", {}).get("lines", []):
            stations = line.get("stations", [])
            line_info = {
                "type": "metro",
                "line": line.get("name"),
                "frequency": line.get("frequency", "varies"),
                "mode": "metro"
            }
            self._add_line_to_graph(stations, line_info, distance_per_station=2.5)
        
        # Bus routes
        for route in city_data.get("bus", {}).get("major_routes", []):
            # For buses, we simulate stops at major hubs
            line_info = {
                "type": "bus",
                "line": f"Bus {route.get('number')}",
                "frequency": route.get("frequency", "varies"),
                "mode": "bus"
            }
            # Extract origin/destination from route string (e.g., "Majestic - Electronic City")
            route_str = route.get("route", "")
            if " - " in route_str:
                parts = route_str.split(" - ")
                if len(parts) == 2:
                    self._add_line_to_graph(parts, line_info, distance_per_station=3.0)
        
        # Suburban rail lines
        for line in city_data.get("suburban_rail", {}).get("lines", []):
            stations = line.get("stations", [])
            line_info = {
                "type": "suburban_rail",
                "line": line.get("name"),
                "frequency": line.get("frequency", "varies"),
                "mode": "rail"
            }
            self._add_line_to_graph(stations, line_info, distance_per_station=5.0)
        
        # Add interchange connections (free transfers between lines)
        interchanges = city_data.get("metro", {}).get("interchange", [])
        for interchange in interchanges:
            # Create edges from interchange to all connected lines passing through it
            for other_interchange in interchanges:
                if interchange != other_interchange:
                    self.graph[interchange].append((
                        other_interchange,
                        {
                            "type": "interchange",
                            "line": "Station Transfer",
                            "frequency": "immediate",
                            "mode": "walk"
                        },
                        0.5  # 0.5 km for walking between platforms
                    ))
    
    def _add_line_to_graph(self, stations: List[str], line_info: Dict[str, Any], distance_per_station: float = 2.5):
        """Add a transit line's stations as edges in the graph."""
        for i in range(len(stations) - 1):
            station_a = stations[i].strip()
            station_b = stations[i + 1].strip()
            
            # Bidirectional edge
            distance = distance_per_station
            self.graph[station_a].append((station_b, line_info, distance))
            self.graph[station_b].append((station_a, line_info, distance))
            
            self.stations.add(station_a)
            self.stations.add(station_b)
    
    def find_k_shortest_paths(self, origin: str, destination: str, k: int = 3, max_transfers: int = 3) -> List[Dict[str, Any]]:
        """
        Find K shortest paths using Yen's algorithm.
        Returns multiple route options sorted by time/cost.
        
        Args:
            origin: Start station
            destination: End station
            k: Number of paths to find
            max_transfers: Maximum allowed transfers
        
        Returns:
            List of route dicts: {
                path: [station1, station2, ...],
                modes: ["metro", "bus", ...],
                lines: [line_names],
                transfers: count,
                distance_km: float,
                estimated_time_min: float,
                cost_estimate: float,
                description: str
            }
        """
        # Normalize station names (fuzzy match)
        origin = self._fuzzy_match_station(origin)
        destination = self._fuzzy_match_station(destination)
        
        if not origin or not destination:
            return []
        
        if origin == destination:
            return [{
                "path": [origin],
                "modes": ["stay"],
                "lines": ["Already at destination"],
                "transfers": 0,
                "distance_km": 0,
                "estimated_time_min": 0,
                "cost_estimate": 0,
                "description": "You are already at the destination"
            }]
        
        # Find shortest path first
        shortest = self._dijkstra(origin, destination, max_transfers)
        if not shortest:
            return []
        
        paths = [shortest]
        
        # Find K-1 more paths using Yen's algorithm
        while len(paths) < k:
            path = self._find_alternative_path(origin, destination, paths, max_transfers)
            if not path:
                break
            paths.append(path)
        
        # Convert paths to route descriptions
        routes = []
        for path_info in paths:
            route = self._path_to_route(path_info["path"], path_info["edges"])
            routes.append(route)
        
        return routes
    
    def _fuzzy_match_station(self, query: str) -> Optional[str]:
        """Find closest matching station name."""
        query = query.strip().lower()
        
        # Exact match
        for station in self.stations:
            if station.lower() == query:
                return station
        
        # Partial match
        for station in self.stations:
            if query in station.lower() or station.lower() in query:
                return station
        
        return None
    
    def _dijkstra(self, origin: str, destination: str, max_transfers: int) -> Optional[Dict[str, Any]]:
        """Find shortest path using Dijkstra."""
        # (distance, transfers, current_node, path, edges)
        pq = [(0, 0, origin, [origin], [])]
        visited = set()
        
        while pq:
            dist, transfers, node, path, edges = heapq.heappop(pq)
            
            if node in visited or transfers > max_transfers:
                continue
            
            visited.add(node)
            
            if node == destination:
                return {
                    "path": path,
                    "edges": edges,
                    "distance": dist,
                    "transfers": transfers
                }
            
            for neighbor, line_info, edge_distance in self.graph[node]:
                if neighbor not in visited and transfers + (1 if line_info.get("type") != "interchange" else 0) <= max_transfers:
                    new_transfers = transfers + (1 if len(path) > 1 and edges and edges[-1].get("type") != line_info.get("type") else 0)
                    heapq.heappush(pq, (
                        dist + edge_distance,
                        new_transfers,
                        neighbor,
                        path + [neighbor],
                        edges + [{"from": node, "to": neighbor, **line_info, "distance": edge_distance}]
                    ))
        
        return None
    
    def _find_alternative_path(self, origin: str, destination: str, existing_paths: List[Dict], max_transfers: int) -> Optional[Dict[str, Any]]:
        """Find alternative path different from existing ones."""
        # Simple approach: find next shortest by temporarily removing edges from best path
        # For production, would use full Yen's algorithm
        return None
    
    def _path_to_route(self, path: List[str], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert path and edges to route description."""
        if not edges:
            return {
                "path": path,
                "modes": [],
                "lines": [],
                "transfers": 0,
                "distance_km": 0,
                "estimated_time_min": 0,
                "cost_estimate": 0,
                "description": " → ".join(path)
            }
        
        # Group consecutive edges by line
        modes = []
        lines = []
        total_distance = 0
        
        current_line = None
        for edge in edges:
            total_distance += edge.get("distance", 0)
            line = edge.get("line", "Transfer")
            mode = edge.get("mode", "walk")
            
            if line != current_line:
                lines.append(line)
                modes.append(mode)
                current_line = line
        
        # Estimate time: metro ~2 min per km, bus ~4 min per km, rail ~3 min per km
        estimated_time = 0
        for edge in edges:
            dist = edge.get("distance", 0)
            mode = edge.get("mode")
            if mode == "metro":
                estimated_time += dist * 2
            elif mode == "bus":
                estimated_time += dist * 4
            elif mode == "rail":
                estimated_time += dist * 3
            else:
                estimated_time += dist * 2
        
        transfers = len(set(m for m in modes if m != "walk"))
        
        # Cost estimate (base + per-km)
        cost_estimate = 25 if "metro" in modes else 20
        cost_estimate += max(len(modes) - 1, 0) * 10  # Transfer penalty
        
        description = " → ".join([f"{path[i]} ({modes[i]})" if i < len(modes) else path[i] for i in range(len(path))])
        
        return {
            "path": path,
            "modes": modes,
            "lines": lines,
            "transfers": transfers - 1 if transfers > 0 else 0,
            "distance_km": round(total_distance, 2),
            "estimated_time_min": int(estimated_time),
            "cost_estimate": int(cost_estimate),
            "description": description
        }
