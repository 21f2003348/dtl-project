"""
API endpoints for Usual Route quick booking feature.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.usual_route import UsualRouteManager

router = APIRouter(prefix="/usual-routes", tags=["Usual Routes"])
usual_route_mgr = UsualRouteManager()


class AddUsualRouteRequest(BaseModel):
    student_id: str = Field(..., description="Student ID")
    route_name: str = Field(..., description="Display name for route (e.g., 'Home to College')")
    origin: str = Field(..., description="Starting location")
    destination: str = Field(..., description="Ending location")
    frequency: str = Field("daily", description="Usage frequency (daily/weekly/occasional)")


class QuickBookRequest(BaseModel):
    student_id: str = Field(..., description="Student ID")
    route_id: str = Field(..., description="Route ID to book")


@router.post("/add")
async def add_usual_route(request: AddUsualRouteRequest) -> Dict[str, Any]:
    """Add a new usual route for quick access."""
    return usual_route_mgr.add_route(
        request.student_id,
        request.route_name,
        request.origin,
        request.destination,
        request.frequency
    )


@router.get("/{student_id}")
async def get_usual_routes(student_id: str) -> Dict[str, Any]:
    """Get all saved usual routes for a student."""
    return usual_route_mgr.get_usual_routes(student_id)


@router.post("/quick-book")
async def quick_book(request: QuickBookRequest) -> Dict[str, Any]:
    """Quick book a saved usual route."""
    return usual_route_mgr.quick_book(request.student_id, request.route_id)


@router.delete("/{student_id}/{route_id}")
async def delete_usual_route(student_id: str, route_id: str) -> Dict[str, Any]:
    """Delete a saved usual route."""
    return usual_route_mgr.delete_route(student_id, route_id)


@router.get("/{student_id}/most-used")
async def get_most_used(student_id: str) -> Dict[str, Any]:
    """Get the most frequently used route for a student."""
    route = usual_route_mgr.get_most_used_route(student_id)
    if route:
        return {"success": True, "route": route}
    return {"success": False, "message": "No routes found"}
