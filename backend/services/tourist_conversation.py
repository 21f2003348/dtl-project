"""
Tourist Conversation Manager - AI-powered conversational recommendations.
Uses Gemini API to understand tourist preferences and recommend places within 50km.
"""
import os
import json
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class TouristSession:
    """Tracks conversation state for a tourist."""
    session_id: str
    location: str = ""
    days: int = 1
    travel_style: str = ""  # adventurer, relaxer, culture_enthusiast
    group_type: str = ""    # solo, couple, family, friends
    interests: List[str] = field(default_factory=list)
    budget: str = "moderate"  # budget, moderate, premium
    preferences_collected: bool = False
    questions_asked: int = 0
    recommendations_given: bool = False


class TouristConversationManager:
    """
    Manages multi-turn conversations with tourists to understand 
    their preferences and provide personalized recommendations.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.sessions: Dict[str, TouristSession] = {}
        
        # Preference questions to ask
        self.question_flow = [
            {
                "key": "travel_style",
                "question": "What kind of traveler are you?",
                "options": ["Adventurer", "Culture Enthusiast", "Relaxed Explorer", "Foodie"]
            },
            {
                "key": "group_type", 
                "question": "Who are you traveling with?",
                "options": ["Solo", "Couple", "Family with kids", "Friends group"]
            },
            {
                "key": "interests",
                "question": "What interests you most?",
                "options": ["Historical sites", "Nature & outdoors", "Local experiences", "Photography spots", "Food & markets"]
            },
            {
                "key": "budget",
                "question": "What's your budget preference?",
                "options": ["Budget-friendly", "Moderate", "Premium experience"]
            }
        ]
    
    def get_or_create_session(self, session_id: str) -> TouristSession:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = TouristSession(session_id=session_id)
        return self.sessions[session_id]
    
    def process_message(self, session_id: str, message: str, 
                        current_state: dict = None) -> Dict[str, Any]:
        """
        Process incoming tourist message and return response with 
        optional follow-up questions or recommendations.
        """
        session = self.get_or_create_session(session_id)
        message_lower = message.lower().strip()
        
        # Check if this is selecting an option from previous question
        if self._is_option_selection(message_lower, session):
            return self._handle_option_selection(session, message_lower)
        
        # Check for location declaration (e.g., "I'm in Hampi for 3 days")
        location_info = self._extract_location_duration(message)
        if location_info:
            session.location = location_info["location"]
            session.days = location_info["days"]
            return self._ask_next_question(session)
        
        # Check for recommendation request
        if self._is_recommendation_request(message_lower):
            if session.location:
                return self._generate_recommendations(session)
            else:
                return {
                    "type": "need_location",
                    "message": "Where are you traveling to? Please tell me the place and how many days you're staying.",
                    "example": "For example: 'I'm in Hampi for 3 days' or 'Visiting Coorg this weekend'"
                }
        
        # Default: Ask for location if not set
        if not session.location:
            return {
                "type": "need_location",
                "message": "Welcome! 🧳 Where are you traveling to and for how long?",
                "example": "Just tell me like: 'I'm in Hampi for 3 days' or 'Visiting Mysore for 2 days'"
            }
        
        # Continue with questions or recommendations
        if not session.preferences_collected:
            return self._ask_next_question(session)
        else:
            return self._generate_recommendations(session)
    
    def _extract_location_duration(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract location and duration from message like 'I'm in Hampi for 3 days'."""
        import re
        message_lower = message.lower().strip()
        
        # Pattern 1: "I'm in Hampi for 3 days" or "visiting Coorg for 2 nights"
        pattern1 = r"(?:i'?m in |i am in |visiting |going to |in )([a-zA-Z\s]+?)\s+for\s+(\d+)\s*(?:day|days|night|nights)"
        match = re.search(pattern1, message_lower)
        if match:
            location = match.group(1).strip().title()
            days = int(match.group(2))
            # Clean up common words
            for word in ["To", "The", "A", "An"]:
                location = location.replace(f" {word} ", " ").strip()
            return {"location": location, "days": days}
        
        # Pattern 2: "3 days in Hampi"
        pattern2 = r"(\d+)\s*(?:day|days|night|nights)\s+(?:in|at)\s+([a-zA-Z\s]+)"
        match = re.search(pattern2, message_lower)
        if match:
            days = int(match.group(1))
            location = match.group(2).strip().title()
            return {"location": location, "days": days}
        
        # Pattern 3: "Hampi for 3 days"
        pattern3 = r"^([a-zA-Z\s]+?)\s+for\s+(\d+)\s*(?:day|days|night|nights)"
        match = re.search(pattern3, message_lower)
        if match:
            location = match.group(1).strip().title()
            days = int(match.group(2))
            return {"location": location, "days": days}
        
        # Pattern 4: Just a location with optional days number - "Hampi" or "Hampi 3"
        words = message.split()
        if len(words) <= 5:
            location_parts = []
            days = 1
            for word in words:
                word_clean = word.strip(".,!?")
                if word_clean.isdigit():
                    days = int(word_clean)
                elif word_clean.lower() not in ["days", "day", "nights", "night", "for", "in", "i'm", "i", "am", "visiting"]:
                    location_parts.append(word_clean.title())
            
            if location_parts:
                location = " ".join(location_parts)
                return {"location": location, "days": days}
        
        return None
    
    def _is_option_selection(self, message: str, session: TouristSession) -> bool:
        """Check if message is selecting an option from a question."""
        if session.questions_asked == 0:
            return False
        
        # Check if it matches any of the expected options
        current_q_idx = session.questions_asked - 1
        if current_q_idx < len(self.question_flow):
            options = self.question_flow[current_q_idx]["options"]
            return any(opt.lower() in message or message in opt.lower() for opt in options)
        return False
    
    def _handle_option_selection(self, session: TouristSession, message: str) -> Dict[str, Any]:
        """Handle user selecting an option."""
        current_q_idx = session.questions_asked - 1
        if current_q_idx >= len(self.question_flow):
            return self._generate_recommendations(session)
        
        question = self.question_flow[current_q_idx]
        key = question["key"]
        
        # Match the selection
        selected = None
        for opt in question["options"]:
            if opt.lower() in message or message in opt.lower():
                selected = opt.lower().replace(" ", "_")
                break
        
        if selected:
            if key == "interests":
                session.interests.append(selected)
            else:
                setattr(session, key, selected)
        
        # Check if we have enough info
        if session.questions_asked >= 2:  # Ask only 2 questions for better UX
            session.preferences_collected = True
            return self._generate_recommendations(session)
        
        return self._ask_next_question(session)
    
    def _is_recommendation_request(self, message: str) -> bool:
        """Check if user is asking for recommendations."""
        keywords = ["recommend", "suggestion", "places", "visit", "see", "explore", 
                    "what to do", "things to do", "attractions", "must see", "best places"]
        return any(kw in message for kw in keywords)
    
    def _ask_next_question(self, session: TouristSession) -> Dict[str, Any]:
        """Ask the next preference question."""
        if session.questions_asked >= len(self.question_flow):
            session.preferences_collected = True
            return self._generate_recommendations(session)
        
        question = self.question_flow[session.questions_asked]
        session.questions_asked += 1
        
        greeting = ""
        if session.questions_asked == 1:
            greeting = f"Great! You're exploring **{session.location}** for **{session.days} days**! 🎉\n\nLet me personalize your experience. "
        
        return {
            "type": "question",
            "message": f"{greeting}{question['question']}",
            "options": question["options"],
            "location": session.location,
            "days": session.days
        }
    
    def _generate_recommendations(self, session: TouristSession) -> Dict[str, Any]:
        """Generate AI-powered recommendations using Gemini."""
        session.recommendations_given = True
        
        # Try Gemini API first
        if self.api_key:
            try:
                recommendations = self._call_gemini(session)
                if recommendations:
                    return recommendations
            except Exception as e:
                print(f"[TOURIST] Gemini API error: {e}")
        
        # Fallback to static recommendations
        return self._generate_fallback_recommendations(session)
    
    def _call_gemini(self, session: TouristSession) -> Optional[Dict[str, Any]]:
        """Call Gemini API for personalized recommendations."""
        prompt = f"""You are a local travel expert. Generate exactly 5 place recommendations for a tourist with these preferences:

Location: {session.location}, India
Duration: {session.days} days
Travel style: {session.travel_style or 'general explorer'}
Traveling with: {session.group_type or 'not specified'}
Interests: {', '.join(session.interests) if session.interests else 'general sightseeing'}
Budget: {session.budget}

Requirements:
- All places MUST be within 50km of {session.location}
- Include a mix of popular and hidden gems
- Be specific with names and distances
- Include practical visiting tips

Return ONLY a valid JSON array with this exact structure (no other text):
[
  {{
    "name": "Place Name",
    "type": "temple/nature/market/museum/viewpoint",
    "description": "2-3 sentence description",
    "distance_km": 5,
    "visit_duration": "2-3 hours",
    "best_time": "Early morning",
    "entry_fee": "Free" or "₹50",
    "tip": "One practical tip"
  }}
]"""

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2000
                }
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                
                # Extract JSON from response
                import re
                json_match = re.search(r'\[[\s\S]*\]', text)
                if json_match:
                    places = json.loads(json_match.group())
                    return self._format_recommendations(session, places)
            
            print(f"[TOURIST] Gemini API returned {response.status_code}")
            return None
            
        except Exception as e:
            print(f"[TOURIST] Gemini error: {e}")
            return None
    
    def _format_recommendations(self, session: TouristSession, places: List[Dict]) -> Dict[str, Any]:
        """Format recommendations for frontend display."""
        # Build day-wise itinerary suggestion
        itinerary = []
        places_per_day = max(2, len(places) // session.days)
        
        for day in range(session.days):
            day_places = places[day * places_per_day:(day + 1) * places_per_day]
            if day_places:
                itinerary.append({
                    "day": day + 1,
                    "places": day_places
                })
        
        return {
            "type": "recommendations",
            "message": f"Here are my top recommendations for your {session.days}-day trip to {session.location}! 🌟",
            "places": places,
            "itinerary": itinerary,
            "location": session.location,
            "days": session.days,
            "personalization": {
                "style": session.travel_style,
                "group": session.group_type,
                "interests": session.interests
            }
        }
    
    def _generate_fallback_recommendations(self, session: TouristSession) -> Dict[str, Any]:
        """Generate static fallback recommendations when API is unavailable."""
        # Popular Indian tourist destinations with nearby places
        location_data = {
            "hampi": [
                {"name": "Virupaksha Temple", "type": "temple", "description": "Ancient temple dedicated to Lord Shiva, one of the oldest functioning temples in India. The main gopuram rises to 50m.", "distance_km": 0, "visit_duration": "2-3 hours", "best_time": "Early morning or sunset", "entry_fee": "₹40", "tip": "Attend the evening Aarti for a spiritual experience"},
                {"name": "Vittala Temple Complex", "type": "temple", "description": "Famous for the iconic Stone Chariot and musical pillars. UNESCO World Heritage site.", "distance_km": 3, "visit_duration": "3-4 hours", "best_time": "Morning (before 11 AM)", "entry_fee": "₹40", "tip": "Reach early to avoid crowds and heat"},
                {"name": "Matanga Hill", "type": "viewpoint", "description": "Highest point in Hampi offering panoramic sunrise/sunset views of the ruins.", "distance_km": 2, "visit_duration": "2 hours", "best_time": "Sunrise", "entry_fee": "Free", "tip": "Start climbing 30 mins before sunrise"},
                {"name": "Coracle Ride", "type": "experience", "description": "Traditional round boat ride on Tungabhadra River, crossing to the other bank.", "distance_km": 1, "visit_duration": "1-2 hours", "best_time": "Late afternoon", "entry_fee": "₹100-150", "tip": "Perfect for couples, negotiate the price"},
                {"name": "Hippie Island (Virupapur Gaddi)", "type": "experience", "description": "Laid-back area across the river with cafes, paddy fields, and boulder landscapes.", "distance_km": 2, "visit_duration": "Half day", "best_time": "Evening", "entry_fee": "Free", "tip": "Great for photography and relaxed vibes"}
            ],
            "default": [
                {"name": "Local Temple", "type": "temple", "description": "Visit the main temple in the area for cultural immersion.", "distance_km": 1, "visit_duration": "1-2 hours", "best_time": "Morning", "entry_fee": "Free", "tip": "Dress modestly"},
                {"name": "Local Market", "type": "market", "description": "Explore local crafts, food, and authentic experiences.", "distance_km": 2, "visit_duration": "2-3 hours", "best_time": "Evening", "entry_fee": "Free", "tip": "Bargain for better prices"},
                {"name": "Scenic Viewpoint", "type": "viewpoint", "description": "Find a hilltop or elevated spot for panoramic views.", "distance_km": 5, "visit_duration": "1-2 hours", "best_time": "Sunrise/Sunset", "entry_fee": "Free", "tip": "Carry water"},
                {"name": "Heritage Walk", "type": "experience", "description": "Take a guided walk through the historic parts of town.", "distance_km": 0, "visit_duration": "2-3 hours", "best_time": "Morning", "entry_fee": "₹200-500", "tip": "Book in advance"},
                {"name": "Local Cuisine Experience", "type": "food", "description": "Try the regional specialties at a local restaurant.", "distance_km": 1, "visit_duration": "1-2 hours", "best_time": "Lunch/Dinner", "entry_fee": "₹200-500", "tip": "Ask locals for recommendations"}
            ]
        }
        
        # Get location-specific or default recommendations
        location_key = session.location.lower().replace(" ", "")
        places = location_data.get(location_key, location_data["default"])
        
        return self._format_recommendations(session, places)


# Global instance
_tourist_manager: Optional[TouristConversationManager] = None


def get_tourist_manager() -> TouristConversationManager:
    """Get or create global tourist conversation manager."""
    global _tourist_manager
    if _tourist_manager is None:
        _tourist_manager = TouristConversationManager()
    return _tourist_manager
