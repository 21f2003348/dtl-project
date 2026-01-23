"""
Tourist AI Planning with dynamic itinerary generation.
Priority: OpenAI -> Gemini -> Hardcoded fallback (Bengaluru only).
"""

from typing import Dict, List, Any, Optional
import os
import requests
import json


class TouristAIPlanner:
    """AI-powered tourist itinerary planner with intelligent provider selection."""
    
    def __init__(self):
        """
        Initialize planner with automatic provider selection.
        Priority: OpenAI -> Gemini -> Hardcoded fallback.
        """
        # Load API keys
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        
        # Verify and select provider
        self.primary_provider = self._verify_and_select_provider()
        
        print(f"[AI PLANNER] Initialized with provider: {self.primary_provider}")
    
    def _verify_and_select_provider(self) -> str:
        """
        Verify API keys and select best available provider.
        
        Returns:
            Provider name: "openai", "gemini", or "fallback"
        """
        # Check OpenAI (Priority 1)
        if self.openai_key and len(self.openai_key.strip()) > 0:
            if self._verify_openai_key():
                print("[AI PLANNER] ✓ OpenAI API key verified - using as primary provider")
                return "openai"
            else:
                print("[AI PLANNER] ✗ OpenAI API key invalid")
        else:
            print("[AI PLANNER] ⊝ OpenAI API key not configured")
        
        # Check Gemini (Priority 2)
        if self.gemini_key and len(self.gemini_key.strip()) > 0:
            if self._verify_gemini_key():
                print("[AI PLANNER] ✓ Gemini API key verified - using as primary provider")
                return "gemini"
            else:
                print("[AI PLANNER] ✗ Gemini API key invalid")
        else:
            print("[AI PLANNER] ⊝ Gemini API key not configured")
        
        # Fallback mode
        print("[AI PLANNER] ⚠️ No valid API keys found - using hardcoded fallback (Bengaluru only)")
        return "fallback"
    
    def _verify_openai_key(self) -> bool:
        """Verify OpenAI API key is valid."""
        try:
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {self.openai_key}"},
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[AI PLANNER] OpenAI verification error: {e}")
            return False
    
    def _verify_gemini_key(self) -> bool:
        """Verify Gemini API key is valid."""
        try:
            # Test Gemini API with a simple model list request
            response = requests.get(
                f"https://generativelanguage.googleapis.com/v1/models?key={self.gemini_key}",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[AI PLANNER] Gemini verification error: {e}")
            return False
    
    def generate_itinerary(
        self,
        city: str,
        days: int = 3,
        interests: List[str] = None,
        budget: str = "moderate",
        travel_style: str = "explorer",
        transport_preference: str = "flexible",
        budget_per_person: int = 3000,
        num_people: int = 1,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate AI-powered itinerary for tourist.
        
        Args:
            city: City name (e.g., "Bengaluru", "Mumbai")
            days: Number of days
            interests: List of interests (e.g., ["temples", "markets", "nature"])
            budget: Budget level (budget/moderate/luxury)
            travel_style: Style (explorer/relaxer/foodie/cultural/elderly)
            transport_preference: Transport mode (public/cabs/flexible)
            budget_per_person: Daily budget per person in rupees
            num_people: Number of people in the group
            language: Language code ("en", "hi", "kn")
        
        Returns:
            {
                "itinerary": [
                    {
                        "day": 1,
                        "morning": {"place": "Vidhana Soudha", "time": "8:00-11:00", "description": "..."},
                        "afternoon": {...},
                        "evening": {...},
                        "tips": "..."
                    },
                    ...
                ],
                "estimated_cost": "₹3000-5000",
                "best_time_to_visit": "Oct-Feb",
                "safety_notes": "..."
            }
        """
        
        prompt = self._build_itinerary_prompt(
            city, days, interests, budget, travel_style, 
            transport_preference, budget_per_person, num_people,
            language
        )
        
        # Priority 1: Try OpenAI
        if self.primary_provider == "openai" or (self.openai_key and self.primary_provider == "fallback"):
            result = self._query_openai(prompt)
            if result and result.get("days"):
                print(f"[AI PLANNER] ✓ Generated itinerary using OpenAI")
                return result
            print(f"[AI PLANNER] ✗ OpenAI failed, trying fallback...")
        
        # Priority 2: Try Gemini
        if self.primary_provider == "gemini" or (self.gemini_key and self.primary_provider == "fallback"):
            result = self._query_gemini(prompt)
            if result and result.get("days"):
                print(f"[AI PLANNER] ✓ Generated itinerary using Gemini")
                return result
            print(f"[AI PLANNER] ✗ Gemini failed, trying fallback...")
        
        # Priority 3: Hardcoded fallback (Bengaluru only)
        return self._generate_fallback(city, days, interests, budget)
    
    
    def _build_itinerary_prompt(
        self, city: str, days: int, interests: Optional[List[str]], 
        budget: str, style: str, transport_preference: str = "flexible",
        budget_per_person: int = 3000, num_people: int = 1,
        language: str = "en"
    ) -> str:
        """Build prompt for LLM."""
        interests_str = ", ".join(interests) if interests else "sightseeing, food, culture"
        
        # Language instruction
        lang_instruction = "GENERATE CONTENT IN ENGLISH."
        if language == "hi":
            lang_instruction = "IMPORTANT: GENERATE THE ENTIRE CONTENT IN HINDI."
        elif language == "kn":
            lang_instruction = "IMPORTANT: GENERATE THE ENTIRE CONTENT IN KANNADA."
        
        # Build transport guidance
        transport_guidance = {
            "public": "Prioritize public transportation (buses, metro, trains). Include specific routes and timing.",
            "cabs": "Recommend private taxis/cabs for convenience. Provide estimated costs.",
            "flexible": "Mix of public transport and cabs based on distance and convenience."
        }.get(transport_preference, "flexible")
        
        # Build elderly-specific guidance
        elderly_note = ""
        if style == "elderly":
            elderly_note = """
IMPORTANT: This itinerary is for ELDERLY travelers. Strict constraints:
- NO adventure sports, trekking, or high-risk activities.
- NO steep climbs, uneven terrain, or long walks.
- Prioritize accessible, flat, and comfortable locations.
- Include frequent rest breaks and comfortable seating.
- Focus on cultural, scenic, and relaxing experiences.
- Ensure easy access to restrooms and medical facilities.
- Transport must be comfortable (AC cabs preferred).
"""
        
        total_budget = budget_per_person * num_people
        
        return f"""
You are an expert tour guide. Create a {days}-day detailed itinerary for {city}.
{lang_instruction}

Group Details:
- Number of People: {num_people}
- Budget Per Person Per Day: ₹{budget_per_person}
- Total Daily Budget: ₹{total_budget}
- Budget Level: {budget}
- Travel Style: {style}
- Interests: {interests_str}
- Transport Preference: {transport_preference}

Transport Guidelines:
{transport_guidance}
{elderly_note}

Format your response as JSON with this structure:
{{
  "title": "X Days in {city}",
  "days": [
    {{
      "day": 1,
      "theme": "Theme of the day",
      "morning": {{
        "time": "8:00-11:00",
        "place": "Place name",
        "description": "What to do and why",
        "est_cost": "₹100-200"
      }},
      "afternoon": {{ same structure }},
      "evening": {{ same structure }},
      "meals": {{"breakfast": "place", "lunch": "place", "dinner": "place"}},
      "transport_tip": "How to get around based on {transport_preference} preference"
    }}
  ],
  "total_estimated_cost": "₹{budget_per_person * days * num_people} (for {num_people} people)",
  "best_months": "Oct-Feb",
  "packing_tips": ["list", "of", "items"],
  "safety_tips": "Important safety advice",
  "local_language_phrases": {{"hello": "word", "thank_you": "word"}}
}}

CRITICAL: Stay within the budget of ₹{budget_per_person} per person per day. Include actual place names and realistic costs.
"""
    
    def _query_openai(self, prompt: str) -> Dict[str, Any]:
        """Query OpenAI API."""
        if not self.openai_key:
            return {}
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_key}"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    if parsed.get("days"):  # Verify it has actual content
                        return parsed
            else:
                print(f"[OPENAI] API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[OPENAI] Error: {e}")
        
        return {}
    
    def _query_gemini(self, prompt: str) -> Dict[str, Any]:
        """Query Google Gemini API."""
        if not self.gemini_key:
            print("[GEMINI] No API key configured")
            return {}
        
        try:
            # Using Gemini 2.5 Flash (free tier check)
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
            print(f"[GEMINI] Calling API with model: gemini-2.5-flash")
            
            # Append instruction for concise JSON
            prompt += "\n\nCRITICAL: Keep descriptions SHORT (max 15 words). output valid JSON only."
            
            response = requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 8000,
                        "response_mime_type": "application/json"
                    }
                },
                timeout=60
            )
            
            print(f"[GEMINI] Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    finish_reason = candidate.get("finishReason", "UNKNOWN")
                    print(f"[GEMINI] Finish reason: {finish_reason}")
                    
                    if "content" in candidate:
                        content = candidate["content"]["parts"][0]["text"]
                        print(f"[GEMINI] Received response, length: {len(content)} chars")
                        
                        # Clean up markdown if present
                        clean_content = content.replace("```json", "").replace("```", "").strip()
                        
                        try:
                            parsed = json.loads(clean_content)
                            if parsed.get("days"):
                                print(f"[GEMINI] Successfully parsed itinerary with {len(parsed['days'])} days")
                                return parsed
                            else:
                                print(f"[GEMINI] Parsed JSON but no 'days' key found.")
                        except json.JSONDecodeError as je:
                            print(f"[GEMINI] JSON parse error: {je}")
                            print(f"[GEMINI] Raw content end: ...{content[-200:]}")
                    else:
                        print(f"[GEMINI] No content in candidate. Blocked? {candidate.get('safetyRatings')}")
                else:
                    print(f"[GEMINI] No candidates in response: {data}")
            else:
                print(f"[GEMINI] API error: {response.status_code}")
                print(f"[GEMINI] Error response: {response.text[:500]}")
        except Exception as e:
            print(f"[GEMINI] Unexpected error: {type(e).__name__}: {e}")
        
        return {}
    
    def _generate_fallback(self, city: str, days: int, interests: Optional[List[str]], budget: str) -> Dict[str, Any]:
        """
        Fallback: Return hardcoded itinerary ONLY for Bengaluru.
        Raise error for other cities.
        """
        if city.lower() not in ["bengaluru", "bangalore"]:
            raise ValueError(
                f"AI services unavailable. Hardcoded itinerary only available for Bengaluru. "
                f"Cannot generate itinerary for {city}. Please configure OpenAI or Gemini API keys."
            )
        
        return {
            "title": f"{days} Days in {city}",
            "days": [],
            "note": "Using hardcoded famous places for Bengaluru. Configure API keys for AI-generated itineraries."
        }
    
    def get_follow_up_questions(self, city: str, itinerary: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate follow-up questions to refine itinerary - not used in simplified flow."""
        return []


