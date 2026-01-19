"""
Tourist-specific routing and AI itinerary planning endpoints.
"""

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import json

from services.tourist_ai_planner import TouristAIPlanner
from services.route_graph import RouteGraph
from services.data_loader import StaticDataStore
from database import get_db
from models import Itinerary, User
from routes.auth_routes import get_user_id_from_token


router = APIRouter(prefix="/tourist", tags=["tourist"])
tourist_ai = TouristAIPlanner(api_type="ollama")  # Uses open-source Ollama by default


# ==================== Request Models ====================

class TouristItineraryRequest(BaseModel):
    """Request for AI-generated itinerary - simplified to essentials only."""
    city: str = "Bengaluru"  # City or area name (e.g., "Mysore", "Bengaluru")
    num_people: int = 1  # Number of tourists in the group
    days: Optional[int] = 1  # Optional: number of days (default 1-day plan)
    interests: Optional[List[str]] = None  # Optional: auto-detected from city


class TouristQuickTipRequest(BaseModel):
    """Request for quick tourist tips."""
    place_name: str  # e.g., "Vidhana Soudha"
    city: str = "Bengaluru"


# ==================== API Endpoints ====================

@router.get("/destinations")
async def get_available_destinations() -> Dict[str, Any]:
    """
    Get list of all available tourist destinations with place counts.
    
    Returns:
    {
        "destinations": [
            {
                "city": "Bengaluru",
                "places_count": 8,
                "popular_places": ["Lalbagh", "Cubbon Park", ...],
                "best_for": ["gardens", "temples", "shopping"]
            },
            ...
        ]
    }
    """
    destinations = []
    
    # Get all cities from famous places database
    famous_places_db = {
        "bengaluru": {
            "display_name": "Bengaluru",
            "state": "Karnataka",
            "popular_places": ["Lalbagh Botanical Garden", "Cubbon Park", "Vidhana Soudha"],
            "best_for": ["gardens", "temples", "shopping", "food"],
            "places_count": 18
        },
        "mumbai": {
            "display_name": "Mumbai",
            "state": "Maharashtra",
            "popular_places": ["Gateway of India", "Marine Drive", "Haji Ali Dargah"],
            "best_for": ["monuments", "shopping", "beaches", "culture"],
            "places_count": 20
        },
        "mysore": {
            "display_name": "Mysore",
            "state": "Karnataka",
            "popular_places": ["Mysore Palace", "Chamundi Hills", "Brindavan Gardens"],
            "best_for": ["heritage", "temples", "nature", "culture"],
            "places_count": 9
        },
        "coorg": {
            "display_name": "Coorg",
            "state": "Karnataka",
            "popular_places": ["Abbey Falls", "Raja's Seat", "Dubare Elephant Camp"],
            "best_for": ["nature", "coffee", "waterfalls", "wildlife"],
            "places_count": 7
        },
        "hampi": {
            "display_name": "Hampi",
            "state": "Karnataka",
            "popular_places": ["Virupaksha Temple", "Vittala Temple", "Matanga Hill"],
            "best_for": ["heritage", "temples", "history", "photography"],
            "places_count": 7
        },
        "gokarna": {
            "display_name": "Gokarna",
            "state": "Karnataka",
            "popular_places": ["Om Beach", "Kudle Beach", "Paradise Beach"],
            "best_for": ["beaches", "temples", "relaxation", "nature"],
            "places_count": 6
        }
    }
    
    for key, info in famous_places_db.items():
        destinations.append({
            "city": info["display_name"],
            "city_key": key,
            "state": info["state"],
            "places_count": info["places_count"],
            "popular_places": info["popular_places"],
            "best_for": info["best_for"]
        })
    
    return {
        "status": "success",
        "destinations": destinations,
        "total_destinations": len(destinations),
        "note": "Select a city to generate detailed itinerary"
    }


@router.post("/itinerary")
async def get_tourist_itinerary(
    payload: TouristItineraryRequest,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Generate AI-powered itinerary with famous tourist places.
    Just provide city/area name and number of people - we handle the rest!
    
    Example:
    {
        "city": "Mysore",
        "num_people": 4,
        "days": 2  // optional
    }
    """
    
    print(f"[ITINERARY] Request received - city={payload.city}, people={payload.num_people}, days={payload.days}")
    print(f"[ITINERARY] Authorization header: {'Present' if authorization else 'Missing'}")
    
    # Auto-detect famous places for the city
    famous_places = _get_famous_places(payload.city)
    
    # If city not found, return available destinations
    if not famous_places:
        # Get available destinations
        available_cities = ["Bengaluru", "Mysore", "Coorg", "Hampi", "Gokarna"]
        return {
            "status": "error",
            "message": f"No itinerary data available for '{payload.city}'",
            "available_destinations": available_cities,
            "suggestion": f"Please select from: {', '.join(available_cities)}",
            "note": "Use GET /tourist/destinations to see detailed information about each city"
        }
    
    # Auto-set interests based on city
    auto_interests = _detect_city_interests(payload.city)
    
    # Generate itinerary with famous places
    itinerary = tourist_ai.generate_itinerary(
        city=payload.city,
        days=payload.days or 1,
        interests=auto_interests,
        budget="moderate",  # Default moderate budget
        travel_style="explorer"  # Default explorer style
    )
    
    # Add famous places to each day
    if famous_places:
        itinerary["must_visit_places"] = famous_places
        itinerary["suggested_order"] = _optimize_place_order(famous_places, payload.city)
        
        # Generate detailed day-wise itinerary with step-by-step instructions
        detailed_itinerary = _generate_detailed_itinerary(
            famous_places, 
            payload.days or 1, 
            payload.city,
            payload.num_people
        )
        itinerary["daily_plan"] = detailed_itinerary
    
    # Auto-save itinerary if user is logged in
    if authorization:
        try:
            token = authorization.replace("Bearer ", "")
            user_id = get_user_id_from_token(token)
            
            if user_id:
                # Verify user exists
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    # Save directly to database
                    new_itinerary = Itinerary(
                        user_id=user_id,
                        title=f"{payload.city} Trip - {payload.days or 1} Days",
                        city=payload.city,
                        days=payload.days or 1,
                        num_people=payload.num_people,
                        itinerary_data=json.dumps(itinerary),
                        interests=",".join(auto_interests) if auto_interests else None,
                        budget="moderate"
                    )
                    
                    db.add(new_itinerary)
                    db.commit()
                    db.refresh(new_itinerary)
                    
                    itinerary["saved"] = True
                    itinerary["itinerary_id"] = new_itinerary.id
                    print(f"[ITINERARY] Auto-saved with ID: {new_itinerary.id} for user {user.username}")
        except Exception as e:
            # Don't fail if save fails, just log and continue
            print(f"[ITINERARY] Auto-save failed: {e}")
            import traceback
            traceback.print_exc()
            itinerary["saved"] = False
    
    return {
        "status": "success",
        "city": payload.city,
        "num_people": payload.num_people,
        "days": payload.days or 1,
        "itinerary": itinerary,
        "famous_places": famous_places,
        "detailed_instructions": itinerary.get("daily_plan", []),
        "note": f"Auto-generated plan for {payload.num_people} {'person' if payload.num_people == 1 else 'people'} visiting famous places in {payload.city}"
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

def _get_famous_places(city: str) -> List[Dict[str, Any]]:
    """Get list of famous tourist places for a city."""
    city_lower = city.lower()
    
    famous_places_db = {
        "bengaluru": [
            {"name": "Lalbagh Botanical Garden", "type": "nature", "time_needed": "2-3 hrs", "entry_fee": "₹40"},
            {"name": "Cubbon Park", "type": "nature", "time_needed": "2 hrs", "entry_fee": "₹30"},
            {"name": "Vidhana Soudha", "type": "architecture", "time_needed": "1 hr", "entry_fee": "Free"},
            {"name": "Bangalore Palace", "type": "heritage", "time_needed": "2 hrs", "entry_fee": "₹280"},
            {"name": "ISKCON Temple", "type": "temple", "time_needed": "1.5 hrs", "entry_fee": "Free"},
            {"name": "Commercial Street", "type": "shopping", "time_needed": "2-3 hrs", "entry_fee": "Free"},
            {"name": "Brigade Road", "type": "shopping", "time_needed": "2 hrs", "entry_fee": "Free"},
            {"name": "KR Market", "type": "market", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Tipu Sultan's Summer Palace", "type": "heritage", "time_needed": "1.5 hrs", "entry_fee": "₹50"},
            {"name": "Nandi Hills", "type": "nature", "time_needed": "3 hrs", "entry_fee": "₹50"},
            {"name": "Ulsoor Lake", "type": "nature", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Attara Kacheri", "type": "heritage", "time_needed": "45 mins", "entry_fee": "Free"},
            {"name": "Vidhanasoudha Light and Sound Show", "type": "entertainment", "time_needed": "2 hrs", "entry_fee": "₹100"},
            {"name": "Bannerghatta National Park", "type": "wildlife", "time_needed": "4-5 hrs", "entry_fee": "₹150"},
            {"name": "High Court Building", "type": "heritage", "time_needed": "1 hr", "entry_fee": "Free"},
            {"name": "Jaganmohan Palace", "type": "heritage", "time_needed": "1.5 hrs", "entry_fee": "₹20"},
            {"name": "Lumbini Gardens", "type": "nature", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Indira Nagar Layout", "type": "shopping", "time_needed": "2-3 hrs", "entry_fee": "Free"}
        ],
        "mumbai": [
            {"name": "Gateway of India", "type": "monument", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Taj Mahal Palace Hotel", "type": "heritage", "time_needed": "1 hr", "entry_fee": "₹500"},
            {"name": "Marine Drive", "type": "nature", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Worli Sea Link", "type": "architecture", "time_needed": "1 hr", "entry_fee": "Free"},
            {"name": "Bandra-Worli Sealink", "type": "architecture", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Haji Ali Dargah", "type": "temple", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Colaba Causeway", "type": "shopping", "time_needed": "2-3 hrs", "entry_fee": "Free"},
            {"name": "Crawford Market", "type": "market", "time_needed": "2 hrs", "entry_fee": "Free"},
            {"name": "Chhatrapati Shivaji Maharaj Vastu Sangrahalaya", "type": "museum", "time_needed": "2-3 hrs", "entry_fee": "₹600"},
            {"name": "Victoria Terminus", "type": "heritage", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "St. Thomas Cathedral", "type": "heritage", "time_needed": "1 hr", "entry_fee": "Free"},
            {"name": "Flora Fountain", "type": "monument", "time_needed": "30 mins", "entry_fee": "Free"},
            {"name": "Hanging Gardens", "type": "nature", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Kamala Nehru Park", "type": "nature", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Mani Bhavan", "type": "heritage", "time_needed": "1-2 hrs", "entry_fee": "₹100"},
            {"name": "Promenade at the Pier", "type": "entertainment", "time_needed": "2-3 hrs", "entry_fee": "Free"},
            {"name": "Phoenix Market City", "type": "shopping", "time_needed": "3-4 hrs", "entry_fee": "Free"},
            {"name": "Siddhivinayak Temple", "type": "temple", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Essel World", "type": "entertainment", "time_needed": "4-5 hrs", "entry_fee": "₹1200"},
            {"name": "Water Kingdom", "type": "entertainment", "time_needed": "4-5 hrs", "entry_fee": "₹1000"}
        ],
        "mysore": [
            {"name": "Mysore Palace", "type": "heritage", "time_needed": "2-3 hrs", "entry_fee": "₹70"},
            {"name": "Chamundi Hills", "type": "temple", "time_needed": "2 hrs", "entry_fee": "Free"},
            {"name": "Brindavan Gardens", "type": "nature", "time_needed": "2-3 hrs", "entry_fee": "₹60"},
            {"name": "St. Philomena's Church", "type": "heritage", "time_needed": "1 hr", "entry_fee": "Free"},
            {"name": "Mysore Zoo", "type": "nature", "time_needed": "3-4 hrs", "entry_fee": "₹80"},
            {"name": "Devaraja Market", "type": "market", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Jaganmohan Palace", "type": "heritage", "time_needed": "1.5 hrs", "entry_fee": "₹50"},
            {"name": "Rail Museum", "type": "museum", "time_needed": "1-2 hrs", "entry_fee": "₹30"},
            {"name": "Government Museum", "type": "museum", "time_needed": "1-2 hrs", "entry_fee": "₹20"}
        ],
        "coorg": [
            {"name": "Abbey Falls", "type": "nature", "time_needed": "1-2 hrs", "entry_fee": "₹20"},
            {"name": "Raja's Seat", "type": "viewpoint", "time_needed": "1 hr", "entry_fee": "₹10"},
            {"name": "Dubare Elephant Camp", "type": "wildlife", "time_needed": "3-4 hrs", "entry_fee": "₹300"},
            {"name": "Talacauvery", "type": "temple", "time_needed": "1.5 hrs", "entry_fee": "Free"},
            {"name": "Namdroling Monastery", "type": "heritage", "time_needed": "1.5 hrs", "entry_fee": "Free"},
            {"name": "Golden Temple Kusala Nagar", "type": "temple", "time_needed": "1.5 hrs", "entry_fee": "Free"},
            {"name": "Iruppu Falls", "type": "nature", "time_needed": "2 hrs", "entry_fee": "Free"}
        ],
        "hampi": [
            {"name": "Virupaksha Temple", "type": "heritage", "time_needed": "1-2 hrs", "entry_fee": "Free"},
            {"name": "Vittala Temple", "type": "heritage", "time_needed": "2-3 hrs", "entry_fee": "₹40"},
            {"name": "Matanga Hill", "type": "viewpoint", "time_needed": "2 hrs", "entry_fee": "Free"},
            {"name": "Lotus Mahal", "type": "heritage", "time_needed": "1 hr", "entry_fee": "₹40"},
            {"name": "Elephant Stables", "type": "heritage", "time_needed": "30 mins", "entry_fee": "₹40"},
            {"name": "Underground Shiva Temple", "type": "temple", "time_needed": "45 mins", "entry_fee": "Free"},
            {"name": "Hemakuta Hill", "type": "nature", "time_needed": "1-2 hrs", "entry_fee": "Free"}
        ],
        "gokarna": [
            {"name": "Om Beach", "type": "beach", "time_needed": "2-3 hrs", "entry_fee": "Free"},
            {"name": "Kudle Beach", "type": "beach", "time_needed": "2 hrs", "entry_fee": "Free"},
            {"name": "Mahabaleshwar Temple", "type": "temple", "time_needed": "1 hr", "entry_fee": "Free"},
            {"name": "Paradise Beach", "type": "beach", "time_needed": "3 hrs", "entry_fee": "Free"},
            {"name": "Half Moon Beach", "type": "beach", "time_needed": "2 hrs", "entry_fee": "Free"},
            {"name": "Yana Caves", "type": "nature", "time_needed": "2-3 hrs", "entry_fee": "₹50"}
        ]
    }
    
    # Try to match city
    for city_key, places in famous_places_db.items():
        if city_key in city_lower or city_lower in city_key:
            return places
    
    # Return empty list if city not found (validation will handle this)
    return []


def _detect_city_interests(city: str) -> List[str]:
    """Auto-detect tourist interests based on city."""
    city_lower = city.lower()
    
    city_interests = {
        "bengaluru": ["gardens", "temples", "shopping", "food"],
        "mysore": ["heritage", "temples", "nature", "culture"],
        "coorg": ["nature", "coffee", "waterfalls", "wildlife"],
        "hampi": ["heritage", "temples", "history", "photography"],
        "gokarna": ["beaches", "temples", "relaxation", "nature"],
        "ooty": ["nature", "tea gardens", "viewpoints", "relaxation"],
        "chikmagalur": ["coffee", "nature", "trekking", "waterfalls"]
    }
    
    for city_key, interests in city_interests.items():
        if city_key in city_lower or city_lower in city_key:
            return interests
    
    return ["sightseeing", "food", "culture"]


def _optimize_place_order(places: List[Dict[str, Any]], city: str) -> List[str]:
    """Suggest optimal visiting order for places."""
    # Simple optimization: temples/heritage in morning, shopping/markets in afternoon/evening
    morning_places = [p["name"] for p in places if p["type"] in ["temple", "heritage", "nature"]]
    afternoon_places = [p["name"] for p in places if p["type"] in ["shopping", "market", "beach"]]
    
    return morning_places + afternoon_places


def _generate_detailed_itinerary(places: List[Dict[str, Any]], days: int, city: str, num_people: int) -> List[Dict[str, Any]]:
    """Generate detailed day-by-day itinerary with step-by-step instructions and transit routes."""
    daily_plans = []
    
    # Get transit routes for the city
    transit_routes_map = _get_city_transit_routes(city)
    
    # Distribute places across days
    places_per_day = max(2, len(places) // days)
    
    for day_num in range(1, days + 1):
        start_idx = (day_num - 1) * places_per_day
        end_idx = start_idx + places_per_day
        day_places = places[start_idx:end_idx] if day_num < days else places[start_idx:]
        
        if not day_places:
            continue
        
        # Generate detailed instructions for the day
        morning_instruction = []
        afternoon_instruction = []
        evening_instruction = []
        
        for i, place in enumerate(day_places):
            place_name = place["name"]
            entry_fee = place.get("entry_fee", "Free")
            time_needed = place.get("time_needed", "2 hrs")
            place_type = place.get("type", "attraction")
            
            # Get transit route for this place
            transit_info = transit_routes_map.get(place_name, {})
            
            # Determine time slot
            if i == 0:  # First place - morning
                time_slot = "8:00 AM - 11:00 AM"
                route_text = _format_transit_route(transit_info, place_name, num_people, "morning")
                morning_instruction = [
                    f"📍 **{place_name}** ({place_type.title()})",
                    f"⏰ Time: {time_slot}",
                    f"💰 Entry: {entry_fee}",
                    f"⌛ Duration: {time_needed}",
                    "",
                    "**🚌 How to Reach:**",
                    route_text,
                    "",
                    "**Step-by-Step:**",
                    f"1. 🌅 Start your day early at {place_name}",
                    f"2. 🎫 Purchase tickets if needed ({entry_fee})",
                    f"3. 🚶 Explore for {time_needed}",
                    f"4. 📸 Don't forget to take photos!",
                    f"5. 🚗 Move to next destination"
                ]
            elif i == 1:  # Second place - afternoon
                time_slot = "12:00 PM - 3:00 PM"
                route_text = _format_transit_route(transit_info, place_name, num_people, "afternoon")
                afternoon_instruction = [
                    f"📍 **{place_name}** ({place_type.title()})",
                    f"⏰ Time: {time_slot}",
                    f"💰 Entry: {entry_fee}",
                    f"⌛ Duration: {time_needed}",
                    "",
                    "**🚌 How to Reach:**",
                    route_text,
                    "",
                    "**Step-by-Step:**",
                    f"1. 🍽️ Have lunch nearby (budget: ₹{200 * num_people} for {num_people} {'person' if num_people == 1 else 'people'})",
                    f"2. 🚶 Head to {place_name}",
                    f"3. 🎫 Entry: {entry_fee}",
                    f"4. 🔍 Explore for {time_needed}",
                    f"5. 💧 Stay hydrated - carry water"
                ]
            else:  # Third place - evening
                time_slot = "4:00 PM - 7:00 PM"
                route_text = _format_transit_route(transit_info, place_name, num_people, "evening")
                evening_instruction = [
                    f"📍 **{place_name}** ({place_type.title()})",
                    f"⏰ Time: {time_slot}",
                    f"💰 Entry: {entry_fee}",
                    f"⌛ Duration: {time_needed}",
                    "",
                    "**🚌 How to Reach:**",
                    route_text,
                    "",
                    "**Step-by-Step:**",
                    f"1. 🌆 Visit {place_name} in the evening",
                    f"2. 🎫 Entry: {entry_fee}",
                    f"3. 👀 Spend {time_needed} exploring",
                    f"4. 🍕 Dinner nearby (budget: ₹{300 * num_people} for {num_people} {'person' if num_people == 1 else 'people'})",
                    f"5. 🏨 Return to hotel/accommodation"
                ]
        
        # Calculate estimated daily cost
        total_entry_fees = sum([
            int(p.get("entry_fee", "₹0").replace("₹", "").replace("Free", "0")) 
            for p in day_places
        ])
        meals_cost = 500 * num_people  # Breakfast, lunch, dinner
        transport_cost = 200 * num_people  # Local transport
        daily_budget = (total_entry_fees * num_people) + meals_cost + transport_cost
        
        daily_plans.append({
            "day": day_num,
            "theme": f"Exploring {city}",
            "places_count": len(day_places),
            "morning": "\n".join(morning_instruction) if morning_instruction else "Free time / breakfast",
            "afternoon": "\n".join(afternoon_instruction) if afternoon_instruction else "Lunch break",
            "evening": "\n".join(evening_instruction) if evening_instruction else "Dinner / rest",
            "estimated_budget": f"₹{daily_budget}",
            "tips": [
                f"🌞 Start early to avoid crowds",
                f"💧 Carry water bottles for {num_people} {'person' if num_people == 1 else 'people'}",
                f"📱 Keep phones charged for navigation",
                f"🎒 Wear comfortable shoes for walking",
                f"💳 Carry cash and cards"
            ]
        })
    
    return daily_plans


def _get_city_transit_routes(city: str) -> Dict[str, Dict[str, Any]]:
    """Get transit route information for each place in the city."""
    routes_db = {
        "Bengaluru": {
            "Lalbagh Botanical Garden": {
                "metro": {"line": "Purple Line", "station": "South End Circle", "distance": "2.5 km"},
                "bus": [{"number": "100", "from": "Majestic", "duration": "45 mins"}, 
                        {"number": "101", "from": "Silk Board", "duration": "30 mins"}],
                "auto": "₹150-200",
                "total_time": "45 mins from city center",
                "best_option": "Metro + 5 min walk (easiest)"
            },
            "Cubbon Park": {
                "metro": {"line": "Purple/Green Line", "station": "Cubbon Park", "distance": "Direct"},
                "bus": [{"number": "42", "from": "Majestic", "duration": "20 mins"},
                        {"number": "43", "from": "Malleshwaram", "duration": "25 mins"}],
                "auto": "₹80-120",
                "total_time": "30 mins from city center",
                "best_option": "Metro direct to station (recommended)"
            },
            "Vidhana Soudha": {
                "metro": {"line": "Purple/Green Line", "station": "Cubbon Park", "distance": "200m walk"},
                "bus": [{"number": "42", "from": "Majestic", "duration": "20 mins"}],
                "auto": "₹100-150",
                "total_time": "25 mins from city center",
                "best_option": "Metro to Cubbon Park, then walk"
            },
            "Bangalore Palace": {
                "metro": {"line": "Green Line", "station": "Vidhana Soudha", "distance": "3 km"},
                "bus": [{"number": "59", "from": "Kempegowda Bus Station", "duration": "50 mins"}],
                "auto": "₹250-350",
                "total_time": "1 hour from city center",
                "best_option": "Metro + auto/auto rickshaw"
            },
            "ISKCON Temple": {
                "metro": {"line": "Yellow Line", "station": "Indiranagar", "distance": "1.5 km"},
                "bus": [{"number": "29", "from": "Majestic", "duration": "40 mins"},
                        {"number": "38", "from": "Jayanagar", "duration": "35 mins"}],
                "auto": "₹120-180",
                "total_time": "40 mins from city center",
                "best_option": "Bus #29 or #38 direct (budget-friendly)"
            },
            "Tipu Sultan's Summer Palace": {
                "metro": {"line": "Purple Line", "station": "South End Circle", "distance": "2 km"},
                "bus": [{"number": "100", "from": "Majestic", "duration": "35 mins"}],
                "auto": "₹150-200",
                "total_time": "40 mins from city center",
                "best_option": "Metro or bus #100"
            },
            "Nandi Hills": {
                "metro": {"line": "No metro access", "station": "Nearest: Whitefield", "distance": "30 km"},
                "bus": [{"number": "KBS", "from": "Kempegowda Bus Station", "duration": "1.5 hours"}],
                "auto": "₹800-1200",
                "total_time": "1.5-2 hours from city center",
                "best_option": "Hired car/taxi (most comfortable for groups)"
            },
            "Commercial Street": {
                "metro": {"line": "Purple/Green Line", "station": "Cubbon Park", "distance": "500m"},
                "bus": [{"number": "42", "from": "Majestic", "duration": "15 mins"}],
                "auto": "₹80-120",
                "total_time": "20 mins from city center",
                "best_option": "Metro to Cubbon Park, walk"
            },
            "Brigade Road": {
                "metro": {"line": "Purple/Green Line", "station": "Cubbon Park", "distance": "600m"},
                "bus": [{"number": "42", "from": "Majestic", "duration": "15 mins"}],
                "auto": "₹100-150",
                "total_time": "20 mins from city center",
                "best_option": "Metro + short walk"
            }
        },
        "Mumbai": {
            "Gateway of India": {
                "metro": {"line": "Line 1", "station": "Reverse Parking", "distance": "500m"},
                "bus": [{"number": "1", "from": "Fort", "duration": "10 mins"},
                        {"number": "3", "from": "Bandra", "duration": "20 mins"}],
                "auto": "₹60-100",
                "total_time": "20 mins from city center",
                "best_option": "Ferry + walk or metro + auto"
            },
            "Marine Drive": {
                "metro": {"line": "Line 1", "station": "Girgaum", "distance": "1 km"},
                "bus": [{"number": "106", "from": "Fort", "duration": "15 mins"}],
                "auto": "₹80-120",
                "total_time": "30 mins from city center",
                "best_option": "Evening walk from Gateway of India (2.5 km)"
            },
            "Haji Ali Dargah": {
                "metro": {"line": "Line 1", "station": "Grant Road", "distance": "1.5 km"},
                "bus": [{"number": "101", "from": "Worli", "duration": "20 mins"}],
                "auto": "₹100-150",
                "total_time": "30 mins from city center",
                "best_option": "Auto/cab (sunset is best time)"
            },
            "Taj Mahal Palace": {
                "metro": {"line": "Line 1", "station": "Reverse Parking", "distance": "500m"},
                "bus": [{"number": "1", "from": "Fort", "duration": "10 mins"}],
                "auto": "₹60-100",
                "total_time": "20 mins from city center",
                "best_option": "Walking from Gateway of India"
            },
            "Colaba Causeway": {
                "metro": {"line": "Line 1", "station": "Reverse Parking", "distance": "1 km"},
                "bus": [{"number": "3", "from": "Bandra", "duration": "30 mins"}],
                "auto": "₹80-120",
                "total_time": "25 mins from city center",
                "best_option": "Walk from Gateway of India area"
            },
            "Crawford Market": {
                "metro": {"line": "Line 1", "station": "Fort", "distance": "500m"},
                "bus": [{"number": "1", "from": "Reverse Parking", "duration": "10 mins"}],
                "auto": "₹60-100",
                "total_time": "15 mins from city center",
                "best_option": "Metro to Fort station, walk"
            },
            "Siddhivinayak Temple": {
                "metro": {"line": "Line 2B", "station": "Bombay Central", "distance": "2 km"},
                "bus": [{"number": "103", "from": "Mahim", "duration": "25 mins"}],
                "auto": "₹120-180",
                "total_time": "40 mins from Gateway area",
                "best_option": "Early morning visit with auto/taxi"
            },
            "Hanging Gardens": {
                "metro": {"line": "Line 1", "station": "Girgaum", "distance": "1.5 km"},
                "bus": [{"number": "106", "from": "Fort", "duration": "30 mins"}],
                "auto": "₹120-150",
                "total_time": "40 mins from city center",
                "best_option": "Climb from Malabar Hill road (scenic)"
            },
            "Essel World": {
                "metro": {"line": "No direct metro", "station": "Nearest: Vile Parle", "distance": "15 km"},
                "bus": [{"number": "315", "from": "Central Station", "duration": "1 hour"}],
                "auto": "₹500-800",
                "total_time": "1.5 hours from city center",
                "best_option": "Hired car/taxi for groups"
            }
        },
        "Mysore": {
            "Mysore Palace": {
                "metro": {"line": "No metro", "station": "N/A", "distance": "Central"},
                "bus": [{"number": "1", "from": "KSRTC Stand", "duration": "20 mins"},
                        {"number": "5", "from": "Narasimharaja Circle", "duration": "25 mins"}],
                "auto": "₹150-200",
                "total_time": "30 mins from city center",
                "best_option": "Auto or city bus #1"
            },
            "Chamundi Hills": {
                "metro": {"line": "No metro", "station": "N/A", "distance": "15 km"},
                "bus": [{"number": "8", "from": "KSRTC Stand", "duration": "45 mins"}],
                "auto": "₹300-400",
                "total_time": "1 hour from city center",
                "best_option": "Morning visit with private transport"
            },
            "Brindavan Gardens": {
                "metro": {"line": "No metro", "station": "N/A", "distance": "20 km"},
                "bus": [{"number": "316", "from": "KSRTC Stand", "duration": "1 hour"}],
                "auto": "₹400-500",
                "total_time": "1.5 hours from city center",
                "best_option": "Hired car recommended for groups"
            }
        },
        "Coorg": {
            "Abbey Falls": {
                "metro": {"line": "No metro", "station": "N/A", "distance": "25 km"},
                "bus": [{"number": "Local", "from": "Madikeri", "duration": "45 mins"}],
                "auto": "₹500-600",
                "total_time": "1 hour from city center",
                "best_option": "Scooter/bike rental or taxi"
            },
            "Dubare Elephant Camp": {
                "metro": {"line": "No metro", "station": "N/A", "distance": "35 km"},
                "bus": [{"number": "Local", "from": "Madikeri", "duration": "1 hour"}],
                "auto": "₹700-900",
                "total_time": "1.5 hours from city center",
                "best_option": "Full-day tour package with transport"
            },
            "Raja's Seat": {
                "metro": {"line": "No metro", "station": "N/A", "distance": "6 km"},
                "bus": [{"number": "Local", "from": "Madikeri", "duration": "20 mins"}],
                "auto": "₹200-250",
                "total_time": "30 mins from city center",
                "best_option": "Auto or scooter rental"
            }
        },
        "Hampi": {
            "Virupaksha Temple": {
                "metro": {"line": "No metro", "station": "N/A", "distance": "Central"},
                "bus": [{"number": "Local", "from": "Hampi Bazaar", "duration": "10 mins"}],
                "auto": "₹100-150",
                "total_time": "15 mins from main area",
                "best_option": "Walking or local auto"
            },
            "Vittala Temple": {
                "metro": {"line": "No metro", "station": "N/A", "distance": "2 km"},
                "bus": [{"number": "Local", "from": "Hampi Bazaar", "duration": "30 mins"}],
                "auto": "₹200-250",
                "total_time": "40 mins from city center",
                "best_option": "Guided tour with transport included"
            }
        },
        "Gokarna": {
            "Om Beach": {
                "metro": {"line": "No metro", "station": "N/A", "distance": "10 km"},
                "bus": [{"number": "Local", "from": "Gokarna Town", "duration": "30 mins"}],
                "auto": "₹300-400",
                "total_time": "1 hour from city center",
                "best_option": "Scooter rental or group taxi"
            },
            "Kudle Beach": {
                "metro": {"line": "No metro", "station": "N/A", "distance": "5 km"},
                "bus": [{"number": "Local", "from": "Gokarna Town", "duration": "20 mins"}],
                "auto": "₹150-200",
                "total_time": "45 mins from main area",
                "best_option": "Trekking or local transport"
            }
        }
    }
    
    return routes_db.get(city, {})


def _format_transit_route(transit_info: Dict[str, Any], place_name: str, num_people: int, time_period: str) -> str:
    """Format transit route information for display."""
    if not transit_info:
        return f"🚕 **Auto/Taxi**: ₹200-400 | **Bus**: Check local BMTC/KSRTC schedule | **Duration**: ~45 mins"
    
    metro_info = transit_info.get("metro", {})
    bus_routes = transit_info.get("bus", [])
    auto_cost = transit_info.get("auto", "₹150-250")
    total_time = transit_info.get("total_time", "~45 mins")
    best_option = transit_info.get("best_option", "Check local transport")
    
    # Build formatted string
    lines = []
    
    # Metro option
    if metro_info.get("line"):
        lines.append(f"🚇 **Metro**: {metro_info['line']} → {metro_info['station']} | Distance: {metro_info['distance']}")
    
    # Bus options
    if bus_routes:
        for bus in bus_routes[:2]:  # Show top 2 bus routes
            lines.append(f"🚌 **Bus {bus['number']}**: From {bus['from']} | ~{bus['duration']}")
    
    # Auto option
    lines.append(f"🚕 **Auto/Taxi**: {auto_cost}")
    
    # Total time
    lines.append(f"⏱️ **Total Time**: {total_time}")
    
    # Best option
    lines.append(f"✨ **Best Option**: {best_option}")
    
    # Cost for group
    cost_multiplier = num_people if "auto" in best_option.lower() or "taxi" in best_option.lower() or "car" in best_option.lower() else 1
    if "metro" in best_option.lower():
        lines.append(f"💰 **Cost for {num_people} people**: ₹{50 * num_people} (metro tickets)")
    
    return "\n".join(lines)


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
