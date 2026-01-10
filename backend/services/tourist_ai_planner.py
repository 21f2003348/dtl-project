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
        """Fallback: Use template-based itinerary."""
        
        bengaluru_fallback = {
            "title": f"{days} Days in {city}",
            "days": [
                {
                    "day": 1,
                    "theme": "Historical & Cultural",
                    "morning": {
                        "time": "8:00-11:00",
                        "place": "Vidhana Soudha",
                        "description": "Visit the iconic government building with neo-Dravidian architecture. Photography allowed on weekends.",
                        "est_cost": "Free"
                    },
                    "afternoon": {
                        "time": "12:00-17:00",
                        "place": "Cubbon Park",
                        "description": "Relaxing walk in 300 acres of green space. See the Attara Kacheri building and museums.",
                        "est_cost": "₹30 entry"
                    },
                    "evening": {
                        "time": "17:00-20:00",
                        "place": "Brigade Road Market",
                        "description": "Shopping and street food. Try local snacks and shop at independent boutiques.",
                        "est_cost": "₹500-1500"
                    },
                    "meals": {
                        "breakfast": "Local dosa at Vidyarthi Bhavan",
                        "lunch": "Meals at Cubbon Park food courts",
                        "dinner": "Street food at Brigade Road"
                    },
                    "transport_tip": "Use metro from Cubbon Park station"
                },
                {
                    "day": 2,
                    "theme": "Markets & Local Life",
                    "morning": {
                        "time": "7:00-11:00",
                        "place": "Krishnarajendra Market",
                        "description": "Bengaluru's oldest and busiest market. See local produce, flowers, and daily commerce.",
                        "est_cost": "Free (shopping optional)"
                    },
                    "afternoon": {
                        "time": "12:00-17:00",
                        "place": "Janardhana Swami Temple",
                        "description": "Ancient temple with intricate carvings in Basavanagudi. Peaceful and historically significant.",
                        "est_cost": "Free"
                    },
                    "evening": {
                        "time": "17:00-20:00",
                        "place": "Lalbagh Botanical Garden",
                        "description": "Beautiful gardens with a glass house. Evening is best for sunset views.",
                        "est_cost": "₹40 entry"
                    },
                    "meals": {
                        "breakfast": "Dosa and coffee at local eatery",
                        "lunch": "Lunch at Meghana Foods (North Indian)",
                        "dinner": "Fine dine at Brigade Road"
                    },
                    "transport_tip": "Metro available to most locations"
                },
                {
                    "day": 3,
                    "theme": "Tech & Modern Bengaluru",
                    "morning": {
                        "time": "9:00-12:00",
                        "place": "Visvesvaraya Industrial & Technological Museum",
                        "description": "Interactive exhibits on science and technology. Great for understanding Bengaluru's IT revolution.",
                        "est_cost": "₹100"
                    },
                    "afternoon": {
                        "time": "12:00-17:00",
                        "place": "Koramangala Locality",
                        "description": "Trendy neighborhood with cafes, galleries, and shopping. Very Instagram-worthy.",
                        "est_cost": "₹500-1000 (food & shopping)"
                    },
                    "evening": {
                        "time": "18:00-21:00",
                        "place": "Forum Mall / UB City",
                        "description": "Shopping, dining, and entertainment. Evening is busiest and most vibrant.",
                        "est_cost": "Variable"
                    },
                    "meals": {
                        "breakfast": "Breakfast at museum cafe",
                        "lunch": "Lunch at Koramangala cafes",
                        "dinner": "International cuisine at premium restaurants"
                    },
                    "transport_tip": "Use Uber/auto for Koramangala area"
                }
            ],
            "total_estimated_cost": "₹2000-5000" if budget == "budget" else "₹5000-10000" if budget == "luxury" else "₹3000-6000",
            "best_months": "October-February (cool weather)",
            "packing_tips": [
                "Light clothing for hot weather",
                "Sunscreen and hat",
                "Comfortable walking shoes",
                "Power bank for phone",
                "Small backpack"
            ],
            "safety_tips": "Bengaluru is generally safe. Avoid walking alone late at night. Use registered taxis/Uber. Keep valuables secure in crowded markets.",
            "local_language_phrases": {
                "hello": "Namaskara",
                "thank_you": "Dhanyavada",
                "please": "Krupa konda",
                "how much": "Etna",
                "delicious": "Rasa"
            }
        }
        
        return bengaluru_fallback if city.lower() == "bengaluru" else self._generate_generic_fallback(city, days)
    
    def _generate_generic_fallback(self, city: str, days: int) -> Dict[str, Any]:
        """Generate generic template for any city."""
        return {
            "title": f"{days} Days in {city}",
            "days": [
                {
                    "day": i,
                    "theme": f"Exploring {city} - Day {i}",
                    "morning": {"place": "TBD", "description": "Visit local markets and breakfast spots"},
                    "afternoon": {"place": "TBD", "description": "Main attractions or museums"},
                    "evening": {"place": "TBD", "description": "Evening walk or dinner"},
                    "transport_tip": "Use local public transport or auto-rickshaws"
                }
                for i in range(1, days + 1)
            ],
            "total_estimated_cost": "Variable based on preferences",
            "best_months": "Check seasonal weather",
            "safety_tips": "Follow local guidelines and travel with others when possible",
            "note": "AI generation failed. Use this as a template and customize for your trip."
        }
    
    def get_follow_up_questions(self, city: str, itinerary: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate follow-up questions to refine itinerary."""
        return [
            {
                "question": "Would you prefer museums or outdoor activities more?",
                "options": ["Museums", "Outdoor/Nature", "Mix of both"]
            },
            {
                "question": "Do you have any food allergies or preferences?",
                "options": ["Vegetarian", "Non-vegetarian", "Any", "Vegan"]
            },
            {
                "question": "What's your fitness level for walking tours?",
                "options": ["Light walker", "Moderate walker", "Heavy hiker"]
            },
            {
                "question": "Would you like to interact with locals and do cultural activities?",
                "options": ["Yes, definitely", "Maybe", "No, prefer independent exploration"]
            }
        ]
