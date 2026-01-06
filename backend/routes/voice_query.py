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

router = APIRouter()


class VoiceQueryRequest(BaseModel):
    audio: str = Field(..., description="Base64 audio payload")
    user_type: Literal["elderly", "tourist", "student"]
    language: Literal["en", "hi", "kn"]
    city: Optional[str] = Field("Bengaluru", description="City context")
    home: Optional[str] = Field(None, description="Student home/hostel")
    destination: Optional[str] = Field(None, description="Target place if known")
    session_id: Optional[str] = Field(None, description="Session identifier")
    distance_km: Optional[float] = Field(5.0, description="Approx distance for fare/time calc")
    days: Optional[int] = Field(1, description="Number of days for tourist itinerary")


def get_data_store(request: Request) -> StaticDataStore:
    return request.app.state.data_store


def get_state_mgr(request: Request) -> ConversationStateManager:
    return request.app.state.state_mgr


@router.post("/voice-query")
async def handle_voice_query(payload: VoiceQueryRequest, data_store: StaticDataStore = Depends(get_data_store), state_mgr: ConversationStateManager = Depends(get_state_mgr), request: Request = None) -> Dict[str, Any]:
    transcript = transcribe_audio(payload.audio, payload.language)
    intent = parse_intent(transcript["text"], payload.user_type)
    city = payload.city or "Bengaluru"
    session_id = payload.session_id or "demo-session"
    session_state = state_mgr.get_state(session_id)

    # Try live distance/time if token is configured; fallback handled in provider.
    origin = payload.home or city
    destination = payload.destination or intent["destination"]
    live_distance_km, live_duration_min = get_distance_time_km_min(origin, destination)

    if payload.user_type == "elderly":
        decision = plan_safe_route(origin, destination, city, data_store.get("transit_metadata") or {}, distance_km=live_distance_km, duration_min=live_duration_min, transit_lines=data_store.get("transit_lines"))
    elif payload.user_type == "tourist":
        itinerary = draft_itinerary(city, data_store.get("tourist_places") or {}, days=payload.days or 1)
        if not validate_itinerary(itinerary, data_store.get("tourist_places") or {}):
            raise HTTPException(status_code=400, detail="Itinerary failed validation")
        decision = {
            "mode": "tourist",
            "decision": "Curated itinerary",
            "route": itinerary,
            "cost": "Budget-aware (stub)",
            "time": "Multi-day",
            "explanation": "Validated against curated dataset"
        }
    else:
        options = compute_options(payload.home or "Home", destination, city, data_store.get("fares") or {}, distance_km=live_distance_km, duration_min=live_duration_min, transit_lines=data_store.get("transit_lines"))
        decision = {
            "mode": "student",
            "decision": "Cheapest vs fastest computed",
            "route": options,
            "cost": options["cheapest"]["cost"],
            "time": options["fastest"]["time"],
            "explanation": "Cheapest uses bus flat fare; fastest uses metro"
        }

    question = next_question(payload.user_type, city, intent, session_state)
    decision.update({
        "transcript": transcript,
        "intent": intent,
        "city": city,
        "follow_up_question": question
    })

    # Increment deterministic question index per user type for next turn.
    key = f"{payload.user_type}_q_index"
    state_mgr.update_state(session_id, {"last_intent": intent, "last_city": city, key: session_state.get(key, 0) + 1})
    return decision
