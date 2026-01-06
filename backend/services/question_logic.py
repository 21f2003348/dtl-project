from typing import Dict, Any


ELDERLY_QUESTIONS = [
    "Is the destination accessible by metro or bus?",
    "Do you prefer fewer interchanges?",
]

TOURIST_QUESTIONS = [
    "How many days do you have?",
    "Do you prefer history, nature, or food?",
]

STUDENT_QUESTIONS = [
    "Should I prioritize cheapest or fastest today?",
    "Are you okay with one metro leg if it is faster?",
]


def next_question(user_type: str, city: str, intent: Dict[str, Any], state: Dict[str, Any]) -> str:
    """Returns a deterministic follow-up question per user type."""
    if user_type == "elderly":
        return ELDERLY_QUESTIONS[state.get("elderly_q_index", 0) % len(ELDERLY_QUESTIONS)]
    if user_type == "tourist":
        return TOURIST_QUESTIONS[state.get("tourist_q_index", 0) % len(TOURIST_QUESTIONS)]
    return STUDENT_QUESTIONS[state.get("student_q_index", 0) % len(STUDENT_QUESTIONS)]
