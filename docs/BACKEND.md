# Backend API Documentation

## Overview

The AI Travel Assistant backend is built with **FastAPI** and provides voice-first, user-type aware route planning for Bengaluru and Mumbai.

**Base URL:** `http://localhost:8000`

---

## User Type Specific Features

| User Type | Priority | Key Service | Output |
|-----------|----------|-------------|--------|
| **Student** | Cheap & Fast | `student_optimizer.py` | All route options with cost/time ranking |
| **Elderly** | Comfort & Safety | `elderly_router.py` | Comfort-scored options (AC, seating, less walking) |
| **Tourist** | Personalized Discovery | `tourist_conversation.py` | AI conversational recommendations |

---

## API Endpoints

### 1. Voice/Text Query

**POST** `/voice-query`

Main endpoint for processing natural language travel queries.

**Request Body:**
```json
{
  "text": "I want to go from Hebbal to Majestic",
  "user_type": "student",  // "student" | "elderly" | "tourist"
  "language": "en",        // "en" | "hi" | "kn"
  "lat": 12.9716,          // Optional: current location
  "lon": 77.5946           // Optional: current location
}
```

**Response (Student):**
```json
{
  "mode": "student",
  "decision": "Route options found",
  "explanation": "From Hebbal to Majestic:\n\n🚌 Cheapest: ₹25 (35 mins) - Bus\n⚡ Fastest: ₹132 (21 mins) - Auto\n\n📋 All Options:\n  • Bus: ₹25 (35 mins)\n  • Metro: ₹40 (28 mins)\n  • Auto: ₹132 (21 mins)",
  "route": {
    "cheapest": { "mode": "Bus", "cost": 25, "time": 35 },
    "fastest": { "mode": "Auto", "cost": 132, "time": 21 },
    "all_options": [...]
  }
}
```

**Response (Elderly):**
```json
{
  "mode": "elderly",
  "decision": "Comfort-ranked route options",
  "explanation": "Route options ranked by comfort:\n\n🏆 Cab - ₹158 (29 mins) [AC] - Comfort: 115/100\nAuto - ₹165 (26 mins) - Comfort: 100/100\nMetro - ₹29 (26 mins) [AC] - Comfort: 70/100\nBus - ₹25 (46 mins) - Comfort: 35/100",
  "all_options": [...],
  "most_comfortable": {...},
  "fastest": {...}
}
```

**Response (Tourist):**
```json
{
  "mode": "tourist",
  "decision": "Let me personalize your trip!",
  "explanation": "Great! You're exploring **Hampi** for **3 days**! 🎉\nWhat kind of traveler are you?",
  "questions": ["Adventurer", "Culture Enthusiast", "Relaxed Explorer", "Foodie"],
  "location": "Hampi",
  "days": 3
}
```

---

### 2. Health Check

**GET** `/health`

Returns server status.

---

### 3. Transcription

**POST** `/transcribe`

Converts audio to text using Whisper.

**Request:**
```json
{
  "audio": "base64_audio_data",
  "language": "en"
}
```

---

## Services Architecture

```
backend/
├── main.py                     # FastAPI app entry point
├── routes/
│   ├── text_query.py           # /voice-query endpoint
│   ├── transcription_routes.py # Audio transcription
│   └── translation_routes.py   # Language translation
└── services/
    ├── intent_parser.py        # NLP for query understanding
    ├── student_optimizer.py    # Cheapest/fastest routes + all_options
    ├── elderly_router.py       # Comfort-scored routing (NEW)
    ├── tourist_conversation.py # AI conversational manager (NEW)
    ├── tourist_ai_planner.py   # Gemini AI recommendations
    ├── transit_data_service.py # OpenCity.in data loader
    ├── hybrid_router.py        # Multi-modal routing
    ├── mapbox_directions.py    # Walking directions
    ├── ride_pricing.py         # Ola/Uber/Rapido estimates
    └── kml_parser.py           # Mumbai data parser
```

---

## Key Services

### Student Optimizer (`student_optimizer.py`)

Computes cheapest vs fastest options for students.

**Output:**
- `cheapest`: Usually bus/metro (lowest cost)
- `fastest`: Usually auto (lowest time)
- `all_options`: Complete list of all route options
- `door_to_door`: Auto/cab with ride-hailing links
- `recommendation`: Summary text

---

### Elderly Router (`elderly_router.py`) — NEW

Computes **comfort-scored** route options for elderly users.

**Comfort Scoring Factors:**
| Factor | Points |
|--------|--------|
| AC availability | +20 |
| Guaranteed seating | +15 |
| Door-to-door service | +25 |
| Minimal walking (<100m) | +20 |
| Fewer transfers | +10 per transfer avoided |
| Off-peak timing | +5 |

**Output:**
- `most_comfortable`: Highest comfort score option
- `fastest`: Lowest time option
- `all_options`: All options sorted by comfort score

---

### Tourist Conversation Manager (`tourist_conversation.py`) — NEW

Manages multi-turn AI conversations with tourists.

**Features:**
- Location/duration extraction from natural language
- Preference questions (travel style, group type, interests)
- Gemini AI integration for personalized recommendations
- 50km radius filtering for nearby places
- Fallback static recommendations for popular destinations

**Supported Locations:**
- Hampi (curated recommendations)
- Any location (generic recommendations or Gemini AI)

---

### Intent Parser (`intent_parser.py`)

Extracts origin, destination, and city from natural language.

**Supported Patterns:**
- "from X to Y" → origin: X, destination: Y
- "X to Y" → origin: X, destination: Y  
- "X from Y" → origin: Y, destination: X
- "to X from Y" → origin: Y, destination: X

---

## Environment Variables

```env
# Required
TOKEN=pk.xxx                    # Mapbox API token

# Optional (Enhanced Features)
GEMINI_API_KEY=xxx              # Gemini AI for tourist recommendations
OPENAI_API_KEY=sk-xxx           # OpenAI for AI planning
GOOGLE_MAPS_API_KEY=xxx         # Traffic data
HUGGINGFACE_API_KEY=xxx         # Whisper transcription
```

---

## Data Sources

| Source | Data | Format | Location |
|--------|------|--------|----------|
| OpenCity.in | BMTC Bus Stops | CSV | `data/bengaluru/bmtc_stops.csv` |
| OpenCity.in | Mumbai BEST | KML | `data/mumbai/best_stops.kml` |
| Created | Namma Metro | JSON | `data/bengaluru/metro_stations.json` |
| Static | Transit Lines | JSON | `data/transit_lines.json` |
| Static | Fare configs | JSON | `data/fares.json` |

---

## Running the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
