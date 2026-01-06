from typing import Dict
import re


def parse_intent(transcript: str, user_type: str) -> Dict[str, str]:
    """Deterministic intent parser with enhanced destination extraction."""
    intent = "plan_trip" if user_type == "tourist" else "route_request"
    
    text_lower = transcript.lower()
    destination = "Unknown"
    origin = None
    
    # Pattern 1: "from X to Y"
    from_to = re.search(r"from\s+([a-z\s,]+?)\s+to\s+([a-z\s,]+?)(?:\.|$|,|\s+in)", text_lower)
    if from_to:
        origin = from_to.group(1).strip().title()
        destination = from_to.group(2).strip().title()
    else:
        # Pattern 2: "to X" or "going to X"
        to_match = re.search(r"(?:to|going to|go to|need to go)\s+([\w\s,]+?)(?:\.|$|,|\s+from)", text_lower)
        if to_match:
            destination = to_match.group(1).strip().title()
        # Pattern 3: Common landmark names
        elif "majestic" in text_lower:
            destination = "Majestic"
        elif "electronic city" in text_lower:
            destination = "Electronic City"
        elif "colaba" in text_lower:
            destination = "Colaba"
        elif "andheri" in text_lower:
            destination = "Andheri"
        elif "koramangala" in text_lower:
            destination = "Koramangala"
    
    return {
        "intent": intent,
        "destination": destination,
        "origin": origin if origin else "current_location"
    }
