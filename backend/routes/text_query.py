from typing import Literal, Optional, Dict, Any

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field

from services.data_loader import StaticDataStore
from services.whisper_stt import transcribe_audio
from services.intent_parser import parse_intent
from services.elderly_router import plan_safe_route
from services.tourist_planner import draft_itinerary, validate_itinerary
from services.student_optimizer import compute_options
from services.question_logic import next_question
from services.conversation_state import ConversationStateManager
from services.distance_provider import get_distance_time_km_min
from services.group_optimizer import GroupOptimizer
from services.traffic_provider import TrafficProvider

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class TranscribeRequest(BaseModel):
    """Request model for audio transcription."""
    audio: str = Field(..., description="Base64 encoded audio data")
    language: Literal["en", "hi", "kn"] = Field("en", description="Language code")


class TranscribeResponse(BaseModel):
    """Response model for audio transcription."""
    text: str = Field("", description="Transcribed text")
    language: str = Field("en", description="Language code")
    engine: str = Field("", description="Transcription engine used")
    error: Optional[str] = Field(None, description="Error message if any")


class TextQueryRequest(BaseModel):
    """Request model for text-based queries (renamed from VoiceQueryRequest)."""
    text: str = Field(..., description="User's text message")
    user_type: Literal["elderly", "tourist", "student"]
    language: Literal["en", "hi", "kn"]
    city: Optional[str] = Field("Bengaluru", description="City context")
    home: Optional[str] = Field(None, description="Student home/hostel")
    destination: Optional[str] = Field(None, description="Target place if known")
    session_id: Optional[str] = Field(None, description="Session identifier")
    distance_km: Optional[float] = Field(5.0, description="Approx distance for fare/time calc")
    days: Optional[int] = Field(1, description="Number of days for tourist itinerary")
    
    # Group composition fields
    group_type: Literal["solo", "elderly_couple", "student_group", "family", "mixed"] = "solo"
    group_size: int = Field(1, ge=1, le=20, description="Number of people in group")
    elderly_count: int = Field(0, ge=0, description="Number of elderly in group")
    student_count: int = Field(0, ge=0, description="Number of students in group")
    children_count: int = Field(0, ge=0, description="Number of children in group")
    accessibility_need: bool = Field(False, description="Wheelchair or mobility assistance needed")


def get_data_store(request: Request) -> StaticDataStore:
    return request.app.state.data_store


def get_state_mgr(request: Request) -> ConversationStateManager:
    return request.app.state.state_mgr


# ============================================
# Transcription Endpoint (for frontend voice input)
# ============================================

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio_endpoint(payload: TranscribeRequest) -> TranscribeResponse:
    """
    Transcribe audio to text using Whisper.
    Frontend calls this endpoint after recording audio.
    The transcribed text is returned for user verification before sending.
    """
    result = transcribe_audio(payload.audio, payload.language)
    return TranscribeResponse(
        text=result.get("text", ""),
        language=result.get("language", payload.language),
        engine=result.get("engine", "unknown"),
        error=result.get("error")
    )


# ============================================
# Text Query Endpoint (main chat handler)
# ============================================

@router.post("/voice-query")
async def handle_text_query(
    payload: TextQueryRequest,
    data_store: StaticDataStore = Depends(get_data_store),
    state_mgr: ConversationStateManager = Depends(get_state_mgr),
    request: Request = None
) -> Dict[str, Any]:
    """
    Handle text-based queries from users.
    Note: This endpoint now expects TEXT input, not audio.
    The 'voice-query' name is kept for backwards compatibility.
    """
    user_text = payload.text.strip()
    intent = parse_intent(user_text, payload.user_type)
    city = payload.city or "Bengaluru"
    session_id = payload.session_id or "demo-session"
    session_state = state_mgr.get_state(session_id)

    # Extract origin from: 1) parsed intent, 2) payload home, 3) session, 4) city default
    parsed_origin = intent.get("origin")
    if parsed_origin and parsed_origin != "current_location":
        origin = parsed_origin
    else:
        origin = payload.home or session_state.get("last_origin") or city
    
    # Extract destination from: 1) payload, 2) parsed intent, 3) session
    destination = payload.destination or intent.get("destination") or session_state.get("last_destination")
    
    # If destination is still Unknown, try to get from session state
    if destination == "Unknown" and session_state.get("last_destination"):
        destination = session_state["last_destination"]
    
    live_distance_km, live_duration_min = get_distance_time_km_min(origin, destination)

    # Initialize group optimizer and traffic provider
    group_optimizer = GroupOptimizer(data_store.get("transit_lines") or {}, data_store.get("fares") or {}, city)
    traffic_provider = TrafficProvider()

    # Check if this is a follow-up answer (select_option intent)
    if intent.get("intent") == "select_option":
        choice = intent.get("choice", "cheapest")
        
        # Get route options from session or compute fresh
        cached_options = session_state.get("last_route_options")
        if not cached_options:
            cached_options = compute_options(
                origin, destination, city, 
                data_store.get("fares") or {}, 
                distance_km=live_distance_km, 
                duration_min=live_duration_min, 
                transit_lines=data_store.get("transit_lines")
            )
        
        # Return the selected option with detailed directions
        selected = cached_options.get(choice, cached_options.get("cheapest"))
        steps_text = selected.get("steps_text", "Take public transport to destination.")
        
        decision = {
            "mode": "student",
            "decision": f"Here's your {choice} route from {origin} to {destination}",
            "selected_option": choice,
            "route": selected,
            "cost": selected.get("cost", "N/A"),
            "time": selected.get("time", "N/A"),
            "explanation": f"📍 {choice.capitalize()} Route ({selected.get('mode', 'Transit')}):\n\n{steps_text}\n\n💰 Total: ₹{selected.get('cost', 'N/A')} | ⏱️ ~{selected.get('time', 'N/A')} mins"
        }
        
        # No more follow-up questions after selection
        decision.update({
            "user_text": user_text,
            "intent": intent,
            "city": city,
            "follow_up_question": "Would you like directions for another route?"
        })
        return decision

    # Check if group travel
    is_group = payload.group_size > 1 or payload.group_type != "solo"
    
    if is_group:
        # Use group optimizer for multi-person travel
        group_result = group_optimizer.compute_group_options(
            origin=origin,
            destination=destination,
            group_type=payload.group_type,
            group_size=payload.group_size,
            elderly_count=payload.elderly_count,
            student_count=payload.student_count,
            children_count=payload.children_count,
            distance_km=live_distance_km,
            duration_min=live_duration_min,
            accessibility_need=payload.accessibility_need
        )
        
        # Get traffic adjustment
        traffic_info = traffic_provider._estimate_by_time_of_day(live_distance_km, live_duration_min)
        
        decision = {
            "mode": "group",
            "decision": "Group-optimized routes",
            "group_summary": group_result["group_summary"],
            "route_options": group_result["route_options"],
            "recommendation": group_result["recommendation"],
            "group_metrics": group_result["group_metrics"],
            "traffic_info": traffic_info,
            "explanation": "Routes optimized for group composition, cost-sharing, and comfort"
        }
    elif payload.user_type == "elderly":
        decision = plan_safe_route(origin, destination, city, data_store.get("transit_metadata") or {}, distance_km=live_distance_km, duration_min=live_duration_min, transit_lines=data_store.get("transit_lines"))
        
        # Build explanation with all options
        most_comfortable = decision.get("most_comfortable", {})
        all_options = decision.get("all_options", [])
        
        if all_options:
            options_text = "\n".join([
                f"{'🏆 ' if i == 0 else ''}{opt.get('mode', 'Option')} - ₹{opt.get('cost', 'N/A')} ({opt.get('time', '?')} mins) {'[AC]' if opt.get('ac') else ''} - Comfort: {opt.get('comfort_score', 0)}/100"
                for i, opt in enumerate(all_options[:4])
            ])
            decision["explanation"] = f"Route options ranked by comfort:\n\n{options_text}\n\n{decision.get('explanation', '')}"
        
        # Add traffic info
        traffic_info = traffic_provider._estimate_by_time_of_day(live_distance_km, live_duration_min)
        decision["traffic_info"] = traffic_info
    elif payload.user_type == "tourist":
        # Use new conversational tourist manager for AI recommendations
        from services.tourist_conversation import get_tourist_manager
        
        tourist_mgr = get_tourist_manager()
        result = tourist_mgr.process_message(
            session_id=session_id,
            message=user_text,
            current_state=session_state
        )
        
        if result.get("type") == "question":
            # Asking preference questions - decision is just a short label
            decision = {
                "mode": "tourist",
                "decision": "Let me personalize your trip!",
                "questions": result.get("options", []),
                "location": result.get("location", ""),
                "days": result.get("days", 1),
                "explanation": result["message"]  # Full message goes here
            }
        elif result.get("type") == "recommendations":
            # AI-generated recommendations
            places_text = "\n".join([
                f"📍 **{p['name']}** ({p.get('distance_km', 0)}km)\n   {p['description']}\n   ⏱️ {p.get('visit_duration', '1-2 hours')} | 💰 {p.get('entry_fee', 'Free')}"
                for p in result.get("places", [])[:5]
            ])
            decision = {
                "mode": "tourist",
                "decision": result["message"],
                "recommendations": result.get("places", []),
                "itinerary": result.get("itinerary", []),
                "explanation": f"{result['message']}\n\n{places_text}",
                "location": result.get("location", ""),
                "days": result.get("days", 1)
            }
        else:
            # Need location or other info
            decision = {
                "mode": "tourist",
                "decision": result.get("message", "Where would you like to explore?"),
                "explanation": result.get("message", "") + (f"\n\n💡 {result.get('example', '')}" if result.get("example") else "")
            }
    else:
        options = compute_options(payload.home or "Home", destination, city, data_store.get("fares") or {}, distance_km=live_distance_km, duration_min=live_duration_min, transit_lines=data_store.get("transit_lines"))
        
        # Build summary with actual costs (not string ₹)
        cheapest = options["cheapest"]
        fastest = options["fastest"]
        all_opts = options.get("all_options", [])
        
        # Build options summary
        options_summary = f"From {origin} to {destination}:\n\n"
        options_summary += f"🚌 **Cheapest**: ₹{cheapest.get('cost', 25)} ({cheapest.get('time', 'N/A')} mins) - {cheapest.get('mode', 'Bus')}\n"
        options_summary += f"⚡ **Fastest**: ₹{fastest.get('cost', 50)} ({fastest.get('time', 'N/A')} mins) - {fastest.get('mode', 'Auto')}"
        
        # Add all options if available
        if len(all_opts) > 2:
            options_summary += "\n\n📋 **All Options:**\n"
            for opt in all_opts:
                mode = opt.get('mode', 'Unknown')
                cost = opt.get('cost', '?')
                time = opt.get('time', '?')
                options_summary += f"  • {mode}: ₹{cost} ({time} mins)\n"
        
        decision = {
            "mode": "student",
            "decision": "Route options found",
            "route": options,
            "all_options": all_opts,
            "cost": cheapest.get("cost", 25),
            "time": fastest.get("time", 20),
            "explanation": options_summary
        }
        
        # Cache options for follow-up
        state_mgr.update_state(session_id, {"last_route_options": options, "last_origin": origin, "last_destination": destination})
        
        # Add traffic info
        traffic_info = traffic_provider._estimate_by_time_of_day(live_distance_km, live_duration_min)
        decision["traffic_info"] = traffic_info

    question = next_question(payload.user_type, city, intent, session_state)
    decision.update({
        "user_text": user_text,
        "intent": intent,
        "city": city,
        "follow_up_question": question
    })

    # Increment deterministic question index per user type for next turn.
    key = f"{payload.user_type}_q_index"
    state_mgr.update_state(session_id, {"last_intent": intent, "last_city": city, "last_origin": origin, "last_destination": destination, key: session_state.get(key, 0) + 1})
    return decision
