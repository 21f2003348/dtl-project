"""
Real-time transit data endpoints using GTFS.
Provides live bus schedules, metro frequencies, and route information.
"""

from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from services.gtfs_loader import GTFSDataLoader, BengaluruTransitData


router = APIRouter(prefix="/transit", tags=["transit"])
gtfs_loader = GTFSDataLoader()


# ==================== Request Models ====================

class NextBusRequest(BaseModel):
    """Request for next bus arrivals."""
    stop_name: str
    route_id: Optional[str] = None


class SearchStopsRequest(BaseModel):
    """Request to search for stops."""
    query: str


class RouteStopsRequest(BaseModel):
    """Request for stops on a specific route."""
    route_id: str


# ==================== API Endpoints ====================

@router.post("/next-buses")
async def get_next_buses(payload: NextBusRequest) -> Dict[str, Any]:
    """
    Get next bus arrivals for a stop.
    
    Example:
    {
        "stop_name": "Majestic",
        "route_id": "215"  # optional
    }
    """
    
    next_buses = gtfs_loader.get_next_bus_times(
        payload.stop_name,
        route_id=payload.route_id,
        limit=5
    )
    
    return {
        "status": "success",
        "stop": payload.stop_name,
        "next_buses": next_buses,
        "note": "Times are estimated if GTFS data is not available"
    }


@router.get("/route-stops/{route_id}")
async def get_route_stops(route_id: str) -> Dict[str, Any]:
    """
    Get all stops on a specific bus route.
    
    Example: /transit/route-stops/215
    """
    
    stops = gtfs_loader.get_route_stops(route_id)
    
    return {
        "status": "success",
        "route_id": route_id,
        "stops": stops,
        "total_stops": len(stops)
    }


@router.post("/search-stops")
async def search_stops(payload: SearchStopsRequest) -> Dict[str, Any]:
    """
    Search for transit stops by name.
    
    Example:
    {
        "query": "Majestic"
    }
    """
    
    results = gtfs_loader.search_stops(payload.query)
    
    return {
        "status": "success",
        "query": payload.query,
        "results": results,
        "count": len(results)
    }


@router.get("/metro-lines")
async def get_metro_lines() -> Dict[str, Any]:
    """Get all Bengaluru metro lines with details."""
    
    metro_data = BengaluruTransitData.METRO_LINES
    
    lines_with_stats = []
    for line_key, line_info in metro_data.items():
        lines_with_stats.append({
            "line_name": line_info["line"],
            "color": line_key,
            "total_stations": len(line_info["stops"]),
            "operational": line_info["operational"],
            "avg_frequency_mins": line_info["frequency_mins"],
            "stops": line_info["stops"]
        })
    
    return {
        "status": "success",
        "metro_lines": lines_with_stats,
        "city": "Bengaluru",
        "total_lines": len(lines_with_stats)
    }


@router.get("/metro-line/{line_color}")
async def get_metro_line_details(line_color: str) -> Dict[str, Any]:
    """
    Get details for a specific metro line.
    
    Example: /transit/metro-line/Purple
    """
    
    metro_data = BengaluruTransitData.METRO_LINES
    line_info = metro_data.get(line_color.capitalize())
    
    if not line_info:
        return {
            "status": "error",
            "message": f"Metro line '{line_color}' not found",
            "available_lines": list(metro_data.keys())
        }
    
    return {
        "status": "success",
        "line": {
            "name": line_info["line"],
            "color": line_color,
            "stops": line_info["stops"],
            "total_stations": len(line_info["stops"]),
            "operational": line_info["operational"],
            "frequency_mins": line_info["frequency_mins"],
            "operating_hours": "05:30 - 23:30",
            "fare_structure": "₹10-50 based on distance"
        }
    }


@router.get("/bus-routes")
async def get_major_bus_routes() -> Dict[str, Any]:
    """Get major BMTC bus routes in Bengaluru."""
    
    routes = BengaluruTransitData.BMTC_MAJOR_ROUTES
    
    return {
        "status": "success",
        "routes": routes,
        "city": "Bengaluru",
        "operator": "BMTC (Bangalore Metropolitan Transport Corporation)",
        "total_routes": len(routes),
        "note": "These are major routes. BMTC operates 300+ routes in total."
    }


@router.get("/bus-route/{route_id}")
async def get_bus_route_details(route_id: str) -> Dict[str, Any]:
    """
    Get details for a specific bus route.
    
    Example: /transit/bus-route/215
    """
    
    # Check in major routes
    major_routes = BengaluruTransitData.BMTC_MAJOR_ROUTES
    route = next((r for r in major_routes if r["route"] == route_id), None)
    
    if not route:
        return {
            "status": "error",
            "message": f"Route {route_id} not found in major routes database"
        }
    
    return {
        "status": "success",
        "route": {
            "route_number": route_id,
            "from": route["from"],
            "to": route["to"],
            "frequency_mins": route["frequency"],
            "operating_hours": "05:30 - 23:30",
            "fare": "₹10-20 based on distance",
            "type": "BMTC Standard",
            "stops": ["Stop 1", "Stop 2", "Stop 3"]  # Would load from GTFS
        }
    }


@router.get("/metro-vs-bus")
async def compare_metro_vs_bus() -> Dict[str, Any]:
    """
    Comparison between metro and bus for travelers.
    """
    
    return {
        "status": "success",
        "comparison": {
            "metro": {
                "pros": [
                    "Fast and reliable",
                    "Climate controlled",
                    "Less traffic impact",
                    "Fixed schedules",
                    "Safe for solo travelers"
                ],
                "cons": [
                    "Limited route coverage",
                    "Limited operating hours (05:30-23:30)",
                    "Crowded during peak hours",
                    "Higher fare in some cases"
                ],
                "best_for": "Daily commuting, long distances, bad weather",
                "avg_speed": "35-40 km/h including stops"
            },
            "bus": {
                "pros": [
                    "Extensive route network (300+ routes)",
                    "Reaches remote areas",
                    "Cheaper fares",
                    "More frequent services"
                ],
                "cons": [
                    "Slower (traffic dependent)",
                    "Crowded during peak hours",
                    "Less comfortable",
                    "Variable schedules"
                ],
                "best_for": "Short trips, reaching neighborhoods, budget travel",
                "avg_speed": "15-25 km/h in city, 30-40 km/h on highways"
            },
            "peak_hours": {
                "weekday_morning": "07:00-10:00",
                "weekday_evening": "17:00-20:00",
                "weekend": "11:00-15:00, 18:00-21:00"
            }
        },
        "recommendation": "Use metro for speed during peak hours, buses for extensive coverage and affordability"
    }


@router.get("/transit-stats/{city}")
async def get_transit_statistics(city: str = "Bengaluru") -> Dict[str, Any]:
    """
    Get transit statistics for a city.
    
    Example: /transit/transit-stats/Bengaluru
    """
    
    if city.lower() == "bengaluru":
        return {
            "status": "success",
            "city": "Bengaluru",
            "metro": {
                "lines": 3,
                "stations": 100,  # Purple + Green + Yellow lines
                "daily_passengers": "~2.2 million",
                "network_length_km": 60
            },
            "buses": {
                "total_routes": 300,
                "daily_passengers": "~45 million",
                "fleet_size": 6100,
                "operator": "BMTC"
            },
            "autos": {
                "total_autos": "~60,000",
                "primary_use": "Short distances and last-mile"
            },
            "taxis": {
                "operators": ["Ola", "Uber", "Rapido"],
                "approx_vehicles": "~100,000"
            }
        }
    else:
        return {
            "status": "error",
            "message": f"Statistics for {city} not available. Currently supporting Bengaluru."
        }
