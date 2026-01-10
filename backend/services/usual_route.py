"""
Usual Route feature for quick bookings.
Stores frequent routes and allows one-click booking for logged-in students.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pathlib import Path


class UsualRouteManager:
    """Manages frequent/usual routes for quick access."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.usual_routes_file = self.data_dir / "usual_routes.json"
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create usual_routes.json if it doesn't exist."""
        if not self.usual_routes_file.exists():
            self.usual_routes_file.write_text(json.dumps({}, indent=2))
    
    def add_route(self, student_id: str, route_name: str, origin: str, destination: str, frequency: str = "daily") -> Dict[str, Any]:
        """
        Add a new usual route for a student.
        
        Args:
            student_id: Student identifier
            route_name: Display name (e.g., "Home to College", "Work")
            origin: Starting location
            destination: Ending location
            frequency: How often used (daily, weekly, occasional)
        
        Returns:
            {success: bool, message: str, route: {...}}
        """
        try:
            routes_data = json.loads(self.usual_routes_file.read_text() or "{}")
            
            if student_id not in routes_data:
                routes_data[student_id] = {"routes": [], "last_used": None}
            
            new_route = {
                "id": f"{student_id}_{route_name.replace(' ', '_').lower()}",
                "name": route_name,
                "origin": origin,
                "destination": destination,
                "frequency": frequency,
                "created_at": datetime.now().isoformat(),
                "last_used": None,
                "usage_count": 0
            }
            
            # Check if route already exists
            existing = next((r for r in routes_data[student_id]["routes"] if r["name"].lower() == route_name.lower()), None)
            if existing:
                return {"success": False, "message": f"Route '{route_name}' already exists"}
            
            routes_data[student_id]["routes"].append(new_route)
            self.usual_routes_file.write_text(json.dumps(routes_data, indent=2))
            
            return {
                "success": True,
                "message": f"Route '{route_name}' added successfully",
                "route": new_route
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def get_usual_routes(self, student_id: str) -> Dict[str, Any]:
        """Get all usual routes for a student."""
        try:
            routes_data = json.loads(self.usual_routes_file.read_text() or "{}")
            student_routes = routes_data.get(student_id, {}).get("routes", [])
            
            # Sort by frequency (daily → weekly → occasional) and last used
            priority = {"daily": 0, "weekly": 1, "occasional": 2}
            sorted_routes = sorted(
                student_routes,
                key=lambda r: (priority.get(r.get("frequency", "occasional"), 3), r.get("last_used") or "")
            )
            
            return {
                "success": True,
                "student_id": student_id,
                "routes": sorted_routes,
                "total": len(sorted_routes)
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}", "routes": []}
    
    def quick_book(self, student_id: str, route_id: str) -> Dict[str, Any]:
        """
        Quick book a usual route (update last_used and increment counter).
        
        Returns route with origin/destination ready for API call.
        """
        try:
            routes_data = json.loads(self.usual_routes_file.read_text() or "{}")
            
            if student_id not in routes_data:
                return {"success": False, "message": "Student not found"}
            
            route = next((r for r in routes_data[student_id]["routes"] if r["id"] == route_id), None)
            if not route:
                return {"success": False, "message": "Route not found"}
            
            # Update last_used and usage_count
            route["last_used"] = datetime.now().isoformat()
            route["usage_count"] = route.get("usage_count", 0) + 1
            
            self.usual_routes_file.write_text(json.dumps(routes_data, indent=2))
            
            return {
                "success": True,
                "message": f"Route '{route['name']}' booked",
                "route": route,
                "query": {
                    "home": route["origin"],
                    "destination": route["destination"],
                    "note": f"Usual route: {route['name']} (used {route['usage_count']} times)"
                }
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def delete_route(self, student_id: str, route_id: str) -> Dict[str, Any]:
        """Delete a usual route."""
        try:
            routes_data = json.loads(self.usual_routes_file.read_text() or "{}")
            
            if student_id not in routes_data:
                return {"success": False, "message": "Student not found"}
            
            original_count = len(routes_data[student_id]["routes"])
            routes_data[student_id]["routes"] = [r for r in routes_data[student_id]["routes"] if r["id"] != route_id]
            
            if len(routes_data[student_id]["routes"]) == original_count:
                return {"success": False, "message": "Route not found"}
            
            self.usual_routes_file.write_text(json.dumps(routes_data, indent=2))
            
            return {"success": True, "message": "Route deleted successfully"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def get_most_used_route(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Get the most frequently used route for a student."""
        try:
            routes_data = json.loads(self.usual_routes_file.read_text() or "{}")
            student_routes = routes_data.get(student_id, {}).get("routes", [])
            
            if not student_routes:
                return None
            
            return max(student_routes, key=lambda r: r.get("usage_count", 0))
        except Exception:
            return None
    
    def suggest_usual_route(self, student_id: str, origin: str, destination: str) -> Optional[Dict[str, Any]]:
        """
        Check if a given origin-destination pair matches a saved usual route.
        Useful for suggesting to save as usual if it's a frequent pattern.
        """
        try:
            routes_data = json.loads(self.usual_routes_file.read_text() or "{}")
            student_routes = routes_data.get(student_id, {}).get("routes", [])
            
            for route in student_routes:
                if (route["origin"].lower() == origin.lower() and 
                    route["destination"].lower() == destination.lower()):
                    return route
            
            return None
        except Exception:
            return None
