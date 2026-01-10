"""
Tourist-specific routing and AI itinerary planning endpoints.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from services.tourist_ai_planner import TouristAIPlanner
from services.route_graph import RouteGraph
from services.data_loader import StaticDataStore


router = APIRouter(prefix="/tourist", tags=["tourist"])
tourist_ai = TouristAIPlanner(api_type="ollama")  # Uses open-source Ollama by default


# ==================== Request Models ====================

class TouristItineraryRequest(BaseModel):
    """Request for AI-generated itinerary."""
    city: str = "Bengaluru"
    days: int = 3
    interests: Optional[List[str]] = None  # ["temples", "markets", "nature", "food"]
    budget: str = "moderate"  # budget, moderate, luxury
    travel_style: str = "explorer"  # explorer, relaxer, foodie, cultural
    language: str = "en"


class TouristQuickTipRequest(BaseModel):
    """Request for quick tourist tips."""
    place_name: str  # e.g., "Vidhana Soudha"
    city: str = "Bengaluru"


# ==================== API Endpoints ====================

@router.post("/itinerary")
async def get_tourist_itinerary(payload: TouristItineraryRequest) -> Dict[str, Any]:
    """
    Generate AI-powered multi-day itinerary for tourists.
    
    Example:
    {
        "city": "Bengaluru",
        "days": 3,
        "interests": ["temples", "markets", "food"],
        "budget": "moderate",
        "travel_style": "explorer"
    }
    """
    
    itinerary = tourist_ai.generate_itinerary(
        city=payload.city,
        days=payload.days,
        interests=payload.interests,
        budget=payload.budget,
        travel_style=payload.travel_style
    )
    
    follow_up_questions = tourist_ai.get_follow_up_questions(payload.city, itinerary)
    
    return {
        "status": "success",
        "itinerary": itinerary,
        "follow_up_questions": follow_up_questions,
        "language": payload.language,
        "note": "Customize this itinerary based on your preferences. Ask for recommendations on specific attractions."
    }


@router.post("/quick-tips")
async def get_quick_tourist_tips(payload: TouristQuickTipRequest) -> Dict[str, Any]:
    """
    Get quick tips for a specific tourist attraction.
    
    Example:
    {
        "place_name": "Vidhana Soudha",
        "city": "Bengaluru"
    }
    """
    
    place_tips = {
        "Vidhana Soudha": {
            "best_time": "Early morning (8-10 AM) or weekend afternoon",
            "entry_fee": "Free",
            "time_needed": "45 minutes to 1 hour",
            "what_to_see": "Stunning neo-Dravidian architecture, government building, surrounding gardens",
            "tips": [
                "Photography allowed on weekends and holidays only",
                "Wear comfortable shoes",
                "Bring water and sunscreen",
                "Visit early to avoid crowds",
                "Nearby: Cubbon Park (5 min walk)"
            ],
            "entry_restrictions": "No large bags, ID required",
            "nearest_metro": "Cubbon Park (Purple Line, Green Line)"
        },
        "Lalbagh Botanical Garden": {
            "best_time": "Early morning (6-10 AM) or sunset (5-7 PM)",
            "entry_fee": "₹40",
            "time_needed": "2-3 hours",
            "what_to_see": "Glass house (replica of Crystal Palace), seasonal flowers, old trees, peaceful gardens",
            "tips": [
                "Best during flower shows (Jan and Aug)",
                "Bring a camera for photography",
                "Wear walking shoes",
                "Early morning has fewer crowds and better light",
                "Good for jogging/walking"
            ],
            "entry_restrictions": "None major",
            "nearest_metro": "South End Circle (Purple Line) - 10 min walk"
        },
        "Brigade Road": {
            "best_time": "Evening (5-8 PM) for shopping, 11 AM-2 PM for breakfast/brunch",
            "entry_fee": "Free",
            "time_needed": "2-3 hours",
            "what_to_see": "Shopping, restaurants, cafes, street food, people watching",
            "tips": [
                "Avoid weekend mornings (very crowded)",
                "Try local street food like Chaat, Samosa",
                "Mix of branded stores and independent boutiques",
                "Plenty of coffee shops",
                "Safe for solo travelers"
            ],
            "entry_restrictions": "None",
            "nearest_metro": "Cubbon Park (Purple, Green) or Trinity Circle (Yellow)"
        },
        "Krishnarajendra Market": {
            "best_time": "Early morning (7-10 AM)",
            "entry_fee": "Free",
            "time_needed": "1-2 hours",
            "what_to_see": "Flowers, vegetables, fruits, spices, traditional commerce, local life",
            "tips": [
                "Visit very early for freshest flowers and produce",
                "Expect crowds and chaos (local experience!)",
                "Bring a bag for shopping",
                "Good photo opportunities",
                "Bargaining possible at some stalls",
                "Not for those sensitive to noise/crowds"
            ],
            "entry_restrictions": "Keep valuables safe",
            "nearest_metro": "KR Market (Purple Line)"
        },
        "Cubbon Park": {
            "best_time": "Early morning (6-10 AM) or late afternoon (4-6 PM)",
            "entry_fee": "₹30",
            "time_needed": "2-3 hours",
            "what_to_see": "300 acres of green space, museums, Attara Kacheri building, lakes, varied flora",
            "tips": [
                "Rent a bicycle for faster exploration",
                "Good for picnics and relaxation",
                "Museums inside: Government Museum, Venkatappa Art Gallery",
                "Morning walk is most popular",
                "Plenty of street food options"
            ],
            "entry_restrictions": "No vehicles inside park",
            "nearest_metro": "Cubbon Park (Purple Line, Green Line)"
        }
    }
    
    tips = place_tips.get(
        payload.place_name,
        {
            "message": f"No specific tips for {payload.place_name}. Try asking about Vidhana Soudha, Lalbagh, Brigade Road, or Cubbon Park.",
            "available_places": list(place_tips.keys())
        }
    )
    
    return {
        "status": "success",
        "place": payload.place_name,
        "city": payload.city,
        "tips": tips
    }


@router.get("/suggested-routes/{origin}/{destination}")
async def get_tourist_friendly_routes(
    origin: str,
    destination: str,
    city: str = "Bengaluru"
) -> Dict[str, Any]:
    """
    Get tourist-friendly routes between two places.
    Prioritizes sightseeing opportunities and scenic routes.
    
    Example: /tourist/suggested-routes/Vidhana%20Soudha/Lalbagh?city=Bengaluru
    """
    
    data_store = StaticDataStore()
    route_graph = RouteGraph(data_store.transit_lines)
    
    # Get standard routes
    routes = route_graph.find_k_shortest_paths(origin, destination, k=3)
    
    # Enhance with tourist notes
    for route in routes:
        attractions_on_way = _get_attractions_on_route(route.get("description", ""))
        route["tourist_note"] = f"This route passes through {attractions_on_way}. Good for exploring!"
        route["scenic_score"] = _calculate_scenic_score(route)
    
    # Sort by scenic score
    routes.sort(key=lambda r: r.get("scenic_score", 0), reverse=True)
    
    return {
        "status": "success",
        "origin": origin,
        "destination": destination,
        "routes": routes[:3],  # Top 3 scenic routes
        "recommendation": "Tourist routes are sorted by scenic value. Consider taking the top route for best sightseeing."
    }


# ==================== Helper Functions ====================

def _get_attractions_on_route(description: str) -> str:
    """Extract attractions mentioned in route description."""
    if "KR Market" in description or "Majestic" in description:
        return "KR Market and Majestic area (historical markets)"
    elif "Lalbagh" in description:
        return "Lalbagh Botanical Garden"
    elif "Jayanagar" in description:
        return "Jayanagar (shopping area)"
    else:
        return "Bengaluru's central attractions"


def _calculate_scenic_score(route: Dict[str, Any]) -> float:
    """Calculate how scenic a route is based on transfers and landmarks."""
    scenic_score = 5.0  # Base score
    
    # Routes with fewer transfers are more scenic
    transfers = route.get("transfers", 0)
    scenic_score -= transfers * 0.5
    
    # Routes through certain areas are more scenic
    description = route.get("description", "").lower()
    scenic_keywords = ["lalbagh", "cubbon", "market", "temple", "garden"]
    for keyword in scenic_keywords:
        if keyword in description:
            scenic_score += 1.5
    
    return max(scenic_score, 1.0)  # Minimum 1.0
