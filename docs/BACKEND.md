# Backend API Documentation

## Overview

The AI Travel Assistant backend is built with **FastAPI** and provides voice-first, user-type aware route planning for Bengaluru and Mumbai.

**Base URL:** `http://localhost:8000`

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
  "route": {
    "cheapest": {
      "mode": "Bus",
      "route": "V-500A",
      "cost": 25,
      "time": 35,
      "steps_text": "🚶 Walk to Hebbal Bus Stop..."
    },
    "fastest": {
      "mode": "Auto",
      "cost": 132,
      "time": 21
    }
  },
  "intent": {
    "origin": "Hebbal",
    "destination": "Majestic",
    "city": "bengaluru"
  },
  "city": "Bengaluru"
}
```

---

### 2. Health Check

**GET** `/health`

Returns server status.

---

### 3. Tourist Itinerary

**POST** `/tourist/plan`

AI-generated sightseeing itineraries for tourists.

**Request:**
```json
{
  "location": "Hampi",
  "interests": ["history", "nature"],
  "days": 2
}
```

---

## Services Architecture

```
backend/
├── main.py                 # FastAPI app entry point
├── routes/
│   ├── text_query.py       # /voice-query endpoint
│   ├── audio.py            # Voice transcription
│   └── geocode.py          # Location services
└── services/
    ├── intent_parser.py    # NLP for query understanding
    ├── student_optimizer.py # Cheapest/fastest routes
    ├── elderly_router.py   # Accessibility-focused routing
    ├── tourist_ai_planner.py # AI itinerary generation
    ├── transit_data_service.py # OpenCity.in data loader
    ├── hybrid_router.py    # Multi-modal routing
    ├── mapbox_directions.py # Walking directions
    ├── ride_pricing.py     # Ola/Uber/Rapido estimates
    └── kml_parser.py       # Mumbai data parser
```

---

## Data Sources

| Source | Data | Format | Location |
|--------|------|--------|----------|
| OpenCity.in | BMTC Bus Stops | CSV | `data/bengaluru/bmtc_stops.csv` |
| OpenCity.in | Mumbai BEST | KML | `data/mumbai/best_stops.kml` |
| Created | Namma Metro | JSON | `data/bengaluru/metro_stations.json` |
| Static | Fare configs | JSON | `data/fares.json` |

---

## Environment Variables

```env
# Required
TOKEN=pk.xxx                    # Mapbox API token

# Optional
OPENAI_API_KEY=sk-xxx           # For AI planning
GOOGLE_MAPS_API_KEY=xxx         # Traffic data
HUGGINGFACE_API_KEY=xxx         # Whisper transcription
```

---

## Key Services

### Intent Parser (`intent_parser.py`)

Extracts origin, destination, and city from natural language.

**Supported Patterns:**
- "from X to Y" → origin: X, destination: Y
- "X to Y" → origin: X, destination: Y  
- "X from Y" → origin: Y, destination: X ✅ Fixed
- "to X from Y" → origin: Y, destination: X

**City Detection:**
- Mumbai keywords: dadar, andheri, bandra, kurla, thane...
- Default: Bengaluru

---

### Transit Data Service (`transit_data_service.py`)

Unified loader for all transit data.

**Features:**
- Loads 2,957 BMTC bus stops
- Loads 77 Namma Metro stations
- Location aliases (Majestic → Kempegowda Bus Station)
- Area-based route search (1-2km radius)

**Alias Examples:**
```python
"majestic" → coordinates (12.9764, 77.5707)
"hebbal" → coordinates (13.0358, 77.5970)
"indiranagar" → coordinates (12.9719, 77.6412)
```

---

### Hybrid Router (`hybrid_router.py`)

Multi-modal route planner combining:
- Walking (Mapbox Directions API)
- Bus (OpenCity BMTC data)
- Metro (Namma Metro JSON)
- Auto/Taxi (fare estimates)

**Route Planning Flow:**
1. Get origin/destination coordinates
2. Find nearest transit stops/stations
3. Find connecting routes
4. Calculate walking + transit + walking segments
5. Return best options sorted by time/cost

---

### Student Optimizer (`student_optimizer.py`)

Computes cheapest vs fastest options for students.

**Output:**
- `cheapest`: Usually bus/metro (lowest cost)
- `fastest`: Usually auto (lowest time)
- `door_to_door`: Auto/cab with ride-hailing links

---

## Error Handling

All endpoints return structured errors:

```json
{
  "error": "Description of error",
  "code": 400
}
```

---

## Running the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
