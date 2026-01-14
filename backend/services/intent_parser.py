from typing import Dict, Optional
import re


def parse_intent(transcript: str, user_type: str) -> Dict[str, str]:
    """Deterministic intent parser with enhanced origin/destination extraction."""
    text_lower = transcript.lower().strip()
    
    # Check for follow-up answers first
    if is_follow_up_answer(text_lower):
        return parse_follow_up(text_lower, user_type)
    
    intent = "plan_trip" if user_type == "tourist" else "route_request"
    destination = None
    origin = None
    
    # Pattern 1: "from X to Y" (e.g., "from Ittamadu to RVCE")
    from_to = re.search(r"from\s+([a-z0-9\s,]+?)\s+to\s+([a-z0-9\s,]+?)(?:\.|$|,|\?|!)", text_lower)
    if from_to:
        origin = from_to.group(1).strip().title()
        destination = from_to.group(2).strip().title()
    
    # Pattern 2: "to X from Y" (e.g., "to RVCE from Ittamadu", "go to RVCE from Banashankari")
    if not origin:
        to_from = re.search(r"(?:go\s+)?to\s+([a-z0-9\s,]+?)\s+from\s+([a-z0-9\s,]+?)(?:\.|$|,|\?|!)", text_lower)
        if to_from:
            destination = to_from.group(1).strip().title()
            origin = to_from.group(2).strip().title()
    
    # Pattern 2.5: "X from Y" without to/go keywords (e.g., "Majestic from Hebbal")
    if not origin and not destination:
        dest_from = re.search(r"^([a-z0-9\s]+?)\s+from\s+([a-z0-9\s]+?)$", text_lower)
        if dest_from:
            destination = dest_from.group(1).strip().title()
            origin = dest_from.group(2).strip().title()
    
    # Pattern 3: "X to Y" without from/to keywords (e.g., "Ittamadu to RVCE")
    if not origin and not destination:
        simple_route = re.search(r"^([a-z0-9\s]+?)\s+to\s+([a-z0-9\s]+?)$", text_lower)
        if simple_route:
            origin = simple_route.group(1).strip().title()
            destination = simple_route.group(2).strip().title()
    
    # Pattern 4: Just "to X" or "go to X" (destination only)
    if not destination:
        to_match = re.search(r"(?:to|going to|go to|reach)\s+([a-z0-9\s,]+?)(?:\.|$|,|\?|!|\s+from)", text_lower)
        if to_match:
            destination = to_match.group(1).strip().title()
    
    # Pattern 5: Common landmark/college names as fallback
    if not destination:
        destination = _extract_landmark(text_lower)
    
    # Also extract origin from known landmarks if still missing
    if not origin or origin == "current_location":
        origin_candidate = _extract_origin_landmark(text_lower, destination)
        if origin_candidate:
            origin = origin_candidate
    
    # Clean up destination if it starts with common words
    if destination:
        destination = re.sub(r"^(go\s+to\s+|to\s+)", "", destination, flags=re.IGNORECASE).strip().title()
        # Handle "Go To Rvce" -> "RVCE"
        if destination.lower() in ["rvce", "go to rvce", "rv college"]:
            destination = "RVCE"
    
    # Detect city from locations
    city = _detect_city(origin, destination, text_lower)
    
    return {
        "intent": intent,
        "destination": destination or "Unknown",
        "origin": origin if origin else "current_location",
        "city": city
    }


def _extract_landmark(text_lower: str) -> Optional[str]:
    """Extract destination from known landmarks."""
    landmarks = {
        "rvce": "RVCE", "rv college": "RVCE",
        "majestic": "Majestic", "kempegowda": "Majestic",
        "electronic city": "Electronic City",
        "koramangala": "Koramangala",
        "banashankari": "Banashankari", "bsk": "Banashankari",
        "jayanagar": "Jayanagar",
        "indiranagar": "Indiranagar",
        "whitefield": "Whitefield",
        "hebbal": "Hebbal",
        "mg road": "MG Road",
        "silk board": "Silk Board",
        "marathahalli": "Marathahalli",
        "kr puram": "KR Puram",
        "yeshwanthpur": "Yeshwanthpur",
        # Mumbai
        "dadar": "Dadar",
        "andheri": "Andheri",
        "bandra": "Bandra",
        "churchgate": "Churchgate",
        "cst": "CST",
        "kurla": "Kurla",
        "borivali": "Borivali"
    }
    for key, value in landmarks.items():
        if key in text_lower:
            return value
    return None


def _extract_origin_landmark(text_lower: str, destination: str) -> Optional[str]:
    """Extract origin from known landmarks."""
    landmarks = {
        "hebbal": "Hebbal",
        "indiranagar": "Indiranagar", 
        "whitefield": "Whitefield",
        "electronic city": "Electronic City",
        "banashankari": "Banashankari", "bsk": "Banashankari",
        "jayanagar": "Jayanagar",
        "koramangala": "Koramangala",
        "marathahalli": "Marathahalli",
        "majestic": "Majestic",
        "mg road": "MG Road",
        "yeshwanthpur": "Yeshwanthpur",
        # Mumbai
        "dadar": "Dadar",
        "andheri": "Andheri",
        "bandra": "Bandra",
        "churchgate": "Churchgate"
    }
    for key, value in landmarks.items():
        if key in text_lower and (not destination or value.lower() != destination.lower()):
            return value
    return None


def _detect_city(origin: str, destination: str, text: str) -> str:
    """Detect city from location names."""
    mumbai_keywords = [
        "dadar", "andheri", "bandra", "kurla", "thane", "borivali",
        "churchgate", "cst", "mumbai", "malad", "goregaon", "kandivali",
        "vashi", "panvel", "navi mumbai", "worli", "lower parel"
    ]
    
    check_text = f"{origin or ''} {destination or ''} {text}".lower()
    
    for kw in mumbai_keywords:
        if kw in check_text:
            return "mumbai"
    
    return "bengaluru"


def is_follow_up_answer(text: str) -> bool:
    """Check if the text is a follow-up answer to a previous question."""
    follow_up_patterns = [
        r"^(cheapest|cheap|budget|affordable)$",
        r"^(fastest|fast|quick|quickest)$",
        r"^(yes|yeah|yep|sure|ok|okay)$",
        r"^(no|nope|nah)$",
        r"^(bus|metro|auto|cab|uber|ola|walk)$",
        r"^(history|nature|food|culture|shopping)$",
        r"^\d+\s*(day|days)?$",  # "3 days" or just "3"
    ]
    for pattern in follow_up_patterns:
        if re.match(pattern, text.strip()):
            return True
    return False


def parse_follow_up(text: str, user_type: str) -> Dict[str, str]:
    """Parse a follow-up answer and return appropriate intent."""
    text = text.strip().lower()
    
    # Preference answers
    if text in ["cheapest", "cheap", "budget", "affordable"]:
        return {
            "intent": "select_option",
            "choice": "cheapest",
            "destination": "Unknown",
            "origin": "current_location"
        }
    elif text in ["fastest", "fast", "quick", "quickest"]:
        return {
            "intent": "select_option",
            "choice": "fastest",
            "destination": "Unknown",
            "origin": "current_location"
        }
    elif text in ["yes", "yeah", "yep", "sure", "ok", "okay"]:
        return {
            "intent": "confirm",
            "choice": "yes",
            "destination": "Unknown",
            "origin": "current_location"
        }
    elif text in ["no", "nope", "nah"]:
        return {
            "intent": "confirm",
            "choice": "no",
            "destination": "Unknown",
            "origin": "current_location"
        }
    elif text in ["bus"]:
        return {"intent": "select_mode", "choice": "bus", "destination": "Unknown", "origin": "current_location"}
    elif text in ["metro"]:
        return {"intent": "select_mode", "choice": "metro", "destination": "Unknown", "origin": "current_location"}
    elif text in ["auto", "cab", "uber", "ola"]:
        return {"intent": "select_mode", "choice": "cab", "destination": "Unknown", "origin": "current_location"}
    
    # Default
    return {
        "intent": "unknown_follow_up",
        "choice": text,
        "destination": "Unknown",
        "origin": "current_location"
    }

