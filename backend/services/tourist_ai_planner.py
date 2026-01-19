"""
Tourist AI Planning with dynamic itinerary generation.
Uses OpenAI API or open-source LLM for smart recommendations.
"""

from typing import Dict, List, Any, Optional
import os
import requests
import json


class TouristAIPlanner:
    """AI-powered tourist itinerary planner."""
    
    def __init__(self, api_type: str = "ollama", model: str = "mistral"):
        """
        Initialize planner with LLM backend.
        
        Args:
            api_type: "openai", "ollama", or "huggingface"
            model: Model name (gpt-3.5-turbo, mistral, etc.)
        """
        self.api_type = api_type
        self.model = model
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    
    def generate_itinerary(
        self,
        city: str,
        days: int = 3,
        interests: List[str] = None,
        budget: str = "moderate",
        travel_style: str = "explorer"
    ) -> Dict[str, Any]:
        """
        Generate AI-powered itinerary for tourist.
        
        Args:
            city: City name (e.g., "Bengaluru", "Mumbai")
            days: Number of days
            interests: List of interests (e.g., ["temples", "markets", "nature"])
            budget: Budget level (budget/moderate/luxury)
            travel_style: Style (explorer/relaxer/foodie/cultural)
        
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
        
        prompt = self._build_itinerary_prompt(city, days, interests, budget, travel_style)
        
        try:
            if self.api_type == "openai" and self.openai_key:
                return self._query_openai(prompt)
            elif self.api_type == "ollama":
                return self._query_ollama(prompt)
            else:
                return self._generate_fallback(city, days, interests, budget)
        except Exception as e:
            print(f"[AI PLANNER] Error: {e}")
            return self._generate_fallback(city, days, interests, budget)
    
    def _build_itinerary_prompt(self, city: str, days: int, interests: Optional[List[str]], budget: str, style: str) -> str:
        """Build prompt for LLM."""
        interests_str = ", ".join(interests) if interests else "sightseeing, food, culture"
        
        return f"""
You are an expert tour guide. Create a {days}-day detailed itinerary for {city}.

Preferences:
- Budget Level: {budget}
- Travel Style: {style}
- Interests: {interests_str}

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
      "transport_tip": "How to get around"
    }}
  ],
  "total_estimated_cost": "₹3000-5000",
  "best_months": "Oct-Feb",
  "packing_tips": ["list", "of", "items"],
  "safety_tips": "Important safety advice",
  "local_language_phrases": {{"hello": "word", "thank_you": "word"}}
}}

Make it practical, budget-conscious, and safe. Include actual place names.
"""
    
    def _query_openai(self, prompt: str) -> Dict[str, Any]:
        """Query OpenAI API."""
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_key}"},
                json={
                    "model": self.model,
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
                    return json.loads(json_match.group())
        except Exception as e:
            print(f"[OPENAI] Error: {e}")
        
        return {}
    
    def _query_ollama(self, prompt: str) -> Dict[str, Any]:
        """Query local Ollama instance (free, open-source)."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7
                },
                timeout=60
            )
            
            if response.status_code == 200:
                content = response.json()["response"]
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            print(f"[OLLAMA] Error: {e}")
        
        return {}
    
    def _generate_fallback(self, city: str, days: int, interests: Optional[List[str]], budget: str) -> Dict[str, Any]:
        """Fallback: Return empty structure - actual places will come from famous_places database."""
        return {
            "title": f"{days} Days in {city}",
            "days": [],
            "note": "Itinerary will be generated from famous places database"
        }
    
    def get_follow_up_questions(self, city: str, itinerary: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate follow-up questions to refine itinerary - not used in simplified flow."""
        return []


