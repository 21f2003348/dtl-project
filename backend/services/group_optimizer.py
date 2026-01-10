"""
Group-aware route optimization.
Recommends routes based on group composition (elderly, students, families, etc.)
"""

from typing import Dict, List, Any, Literal
from services.route_graph import RouteGraph


class GroupOptimizer:
    """Optimizes route recommendations based on group size and composition."""
    
    def __init__(self, transit_lines: Dict[str, Any], fares: Dict[str, Any], city: str = "Bengaluru"):
        self.graph = RouteGraph(transit_lines, city)
        self.transit_lines = transit_lines
        self.fares = fares
        self.city = city
        self.city_fares = fares.get("cities", {}).get(city, {})
    
    def compute_group_options(
        self,
        origin: str,
        destination: str,
        group_type: Literal["solo", "elderly_couple", "student_group", "family", "mixed"],
        group_size: int = 1,
        elderly_count: int = 0,
        student_count: int = 0,
        children_count: int = 0,
        distance_km: float = 5.0,
        duration_min: float = 10.0,
        accessibility_need: bool = False
    ) -> Dict[str, Any]:
        """
        Compute route options optimized for group composition.
        
        Returns:
            {
                "group_summary": str,
                "route_options": [
                    {
                        "route_name": "Cheapest Share",
                        "description": "Bus + shared cab for long distances",
                        "cost_per_person": 45,
                        "total_cost": 180,
                        "time_min": 35,
                        "transfers": 1,
                        "comfort_score": 6,
                        "best_for": "Budget-conscious groups",
                        "suitable_for_group": True,
                        "reason": "Per-person cost lower, time reasonable"
                    },
                    ...
                ],
                "recommendation": str,
                "group_metrics": {
                    "total_cost": int,
                    "per_person_cost": float,
                    "time_estimate": int,
                    "accessibility_friendly": bool
                }
            }
        """
        
        # Find multiple routes using graph
        all_routes = self.graph.find_k_shortest_paths(origin, destination, k=3)
        
        # Filter by accessibility if needed
        if accessibility_need:
            all_routes = self._filter_accessible_routes(all_routes)
        
        # Score and adapt routes for group
        group_options = []
        
        if group_type == "solo":
            group_options = self._solo_options(all_routes)
        elif group_type == "student_group":
            group_options = self._student_group_options(all_routes, group_size, student_count)
        elif group_type == "elderly_couple":
            group_options = self._elderly_couple_options(all_routes, elderly_count)
        elif group_type == "family":
            group_options = self._family_options(all_routes, group_size, children_count)
        elif group_type == "mixed":
            group_options = self._mixed_group_options(all_routes, elderly_count, student_count, children_count)
        
        # Calculate group metrics
        if group_options:
            best_route = group_options[0]
            total_cost = best_route.get("total_cost", 0)
            per_person = total_cost / group_size if group_size > 0 else total_cost
        else:
            total_cost = int(distance_km * 15)  # Fallback estimate
            per_person = total_cost / group_size if group_size > 0 else total_cost
        
        return {
            "group_summary": self._generate_group_summary(group_type, group_size, elderly_count, student_count, children_count),
            "route_options": group_options,
            "recommendation": self._generate_group_recommendation(group_type, group_options),
            "group_metrics": {
                "total_cost": total_cost,
                "per_person_cost": round(per_person, 2),
                "time_estimate": int(duration_min),
                "group_size": group_size,
                "accessibility_friendly": accessibility_need and len(all_routes) > 0
            }
        }
    
    def _solo_options(self, routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Options for single traveler."""
        options = []
        
        # Cheapest
        if len(routes) > 0:
            options.append({
                "route_name": "Most Economical",
                "description": routes[0].get("description", ""),
                "cost_per_person": routes[0].get("cost_estimate", 30),
                "total_cost": routes[0].get("cost_estimate", 30),
                "time_min": routes[0].get("estimated_time_min", 20),
                "transfers": routes[0].get("transfers", 0),
                "comfort_score": 6 - routes[0].get("transfers", 0),
                "best_for": "Budget travelers",
                "suitable_for_group": True,
                "reason": "Lowest total cost"
            })
        
        # Fastest
        if len(routes) > 1:
            options.append({
                "route_name": "Fastest Route",
                "description": routes[1].get("description", ""),
                "cost_per_person": routes[1].get("cost_estimate", 40),
                "total_cost": routes[1].get("cost_estimate", 40),
                "time_min": routes[1].get("estimated_time_min", 15),
                "transfers": routes[1].get("transfers", 0),
                "comfort_score": 7,
                "best_for": "Time-conscious travelers",
                "suitable_for_group": True,
                "reason": "Shortest travel time"
            })
        
        return options[:2]
    
    def _student_group_options(self, routes: List[Dict[str, Any]], group_size: int, student_count: int) -> List[Dict[str, Any]]:
        """Options for student groups with cost-sharing benefits."""
        options = []
        
        if group_size < 2:
            return self._solo_options(routes)
        
        # Shared auto/cab option (splits cost)
        auto_base = self.city_fares.get("auto_base", 35)
        auto_per_km = self.city_fares.get("auto_per_km", 18)
        
        if len(routes) > 0:
            base_cost = routes[0].get("cost_estimate", 30)
            
            # Bus option
            options.append({
                "route_name": "Budget Bus (Cheapest)",
                "description": "Public bus - cheapest for groups",
                "cost_per_person": self.city_fares.get("bus_flat", 20),
                "total_cost": self.city_fares.get("bus_flat", 20) * group_size,
                "time_min": routes[0].get("estimated_time_min", 25),
                "transfers": routes[0].get("transfers", 0),
                "comfort_score": 5,
                "best_for": "Large student groups",
                "suitable_for_group": True,
                "reason": f"Only ₹{self.city_fares.get('bus_flat', 20)}/person, total ₹{self.city_fares.get('bus_flat', 20) * group_size}"
            })
            
            # Shared cab option
            shared_cost = auto_base + (routes[0].get("distance_km", 5) * auto_per_km)
            per_person_shared = shared_cost / group_size
            
            options.append({
                "route_name": "Shared Cab (Fast & Affordable)",
                "description": "Split a cab cost among group members",
                "cost_per_person": int(per_person_shared),
                "total_cost": int(shared_cost),
                "time_min": int(routes[0].get("estimated_time_min", 20) * 0.7),
                "transfers": 0,
                "comfort_score": 7,
                "best_for": "Medium-sized groups",
                "suitable_for_group": True,
                "reason": f"Only ₹{int(per_person_shared)}/person when shared among {group_size} friends"
            })
        
        return options[:2]
    
    def _elderly_couple_options(self, routes: List[Dict[str, Any]], elderly_count: int) -> List[Dict[str, Any]]:
        """Options prioritizing safety and comfort for elderly."""
        options = []
        
        if len(routes) > 0:
            # Safe metro option (accessible)
            metro_cost = self.city_fares.get("metro_per_km", 4) * routes[0].get("distance_km", 5)
            options.append({
                "route_name": "Safe Metro Route",
                "description": "Metro with elevators and accessible facilities",
                "cost_per_person": max(20, int(metro_cost)),
                "total_cost": max(20, int(metro_cost)) * elderly_count,
                "time_min": routes[0].get("estimated_time_min", 25) + 10,  # Add buffer
                "transfers": routes[0].get("transfers", 0),
                "comfort_score": 8,
                "best_for": "Elderly travelers valuing safety",
                "suitable_for_group": True,
                "reason": "Accessible, predictable stops, air-conditioned"
            })
            
            # Comfortable cab option
            auto_base = self.city_fares.get("auto_base", 35)
            auto_per_km = self.city_fares.get("auto_per_km", 18)
            cab_cost = auto_base + (routes[0].get("distance_km", 5) * auto_per_km)
            
            options.append({
                "route_name": "Direct Cab (Door-to-Door)",
                "description": "Private cab with no transfers or crowds",
                "cost_per_person": int(cab_cost / elderly_count) if elderly_count > 0 else int(cab_cost),
                "total_cost": int(cab_cost),
                "time_min": int(routes[0].get("estimated_time_min", 20) * 0.8),
                "transfers": 0,
                "comfort_score": 9,
                "best_for": "Elderly valuing comfort over cost",
                "suitable_for_group": True,
                "reason": "No waiting, no crowds, direct route"
            })
        
        return options[:2]
    
    def _family_options(self, routes: List[Dict[str, Any]], group_size: int, children_count: int) -> List[Dict[str, Any]]:
        """Options considering family comfort, child safety, and luggage."""
        options = []
        
        if len(routes) > 0:
            # Metro with stroller space
            metro_cost = self.city_fares.get("metro_per_km", 4) * routes[0].get("distance_km", 5)
            options.append({
                "route_name": "Family Metro (Space for Stroller)",
                "description": "Metro with designated family zone",
                "cost_per_person": max(20, int(metro_cost)),
                "total_cost": max(20, int(metro_cost)) * group_size,
                "time_min": routes[0].get("estimated_time_min", 25),
                "transfers": routes[0].get("transfers", 0),
                "comfort_score": 7,
                "best_for": "Families with young children",
                "suitable_for_group": True,
                "reason": f"Stroller space available, kid-friendly, ₹{max(20, int(metro_cost))}/person"
            })
            
            # Family cab option (larger vehicle)
            auto_cost = self.city_fares.get("auto_base", 35) + (routes[0].get("distance_km", 5) * 18)
            
            options.append({
                "route_name": "Family Cab (SUV/Innova)",
                "description": "Spacious vehicle for comfort and luggage",
                "cost_per_person": int(auto_cost / group_size) if group_size > 0 else int(auto_cost),
                "total_cost": int(auto_cost),
                "time_min": int(routes[0].get("estimated_time_min", 20) * 0.8),
                "transfers": 0,
                "comfort_score": 9,
                "best_for": "Families with luggage or young children",
                "suitable_for_group": True,
                "reason": "Spacious, luggage-friendly, direct route"
            })
        
        return options[:2]
    
    def _mixed_group_options(self, routes: List[Dict[str, Any]], elderly_count: int, student_count: int, children_count: int) -> List[Dict[str, Any]]:
        """Options for mixed groups with diverse needs."""
        options = []
        
        if len(routes) > 0:
            # Safe balanced option
            metro_cost = self.city_fares.get("metro_per_km", 4) * routes[0].get("distance_km", 5)
            options.append({
                "route_name": "Balanced Route (Safe & Affordable)",
                "description": "Metro + walk, balance of safety and cost",
                "cost_per_person": max(20, int(metro_cost)),
                "total_cost": max(20, int(metro_cost)) * (elderly_count + student_count + children_count),
                "time_min": routes[0].get("estimated_time_min", 25),
                "transfers": routes[0].get("transfers", 0),
                "comfort_score": 7,
                "best_for": "Mixed groups needing compromise",
                "suitable_for_group": True,
                "reason": "Safe for elderly, affordable for students, kid-friendly"
            })
        
        return options[:1]
    
    def _filter_accessible_routes(self, routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter routes to show only those with accessibility features."""
        # Prioritize metro (accessible) over bus
        accessible = [r for r in routes if "metro" in r.get("modes", [])]
        if accessible:
            return accessible[:2]
        return routes[:1]
    
    def _generate_group_summary(self, group_type: str, group_size: int, elderly_count: int, student_count: int, children_count: int) -> str:
        """Generate human-readable group summary."""
        parts = []
        if group_type == "solo":
            return "Solo traveler"
        if elderly_count > 0:
            parts.append(f"{elderly_count} elderly")
        if student_count > 0:
            parts.append(f"{student_count} students")
        if children_count > 0:
            parts.append(f"{children_count} children")
        if group_size > sum([elderly_count, student_count, children_count]):
            parts.append("others")
        
        return f"Group: {', '.join(parts)} ({group_size} total)"
    
    def _generate_group_recommendation(self, group_type: str, options: List[Dict[str, Any]]) -> str:
        """Generate group-specific recommendation."""
        if not options:
            return "No suitable routes found"
        
        best = options[0]
        reason = best.get("reason", "")
        
        if group_type == "student_group":
            return f"Recommended: {best['route_name']} - {reason}"
        elif group_type == "elderly_couple":
            return f"Recommended: {best['route_name']} - Prioritizes safety and comfort"
        elif group_type == "family":
            return f"Recommended: {best['route_name']} - Considerate of children and luggage"
        else:
            return f"Recommended: {best['route_name']} - {reason}"
