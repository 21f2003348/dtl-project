# Technical Documentation

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Landing  │  │ Student  │  │ Elderly  │  │ Tourist  │     │
│  │  Page    │  │   Mode   │  │   Mode   │  │   Mode   │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │             │             │            │
│       └─────────────┴─────────────┴─────────────┘            │
│                         │                                    │
│                         ▼                                    │
│              ┌─────────────────────┐                         │
│              │     chat.js         │                         │
│              │  (Voice + Text UI)  │                         │
│              └──────────┬──────────┘                         │
└─────────────────────────┼────────────────────────────────────┘
                          │ HTTP POST
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    FastAPI App                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │   │
│  │  │/voice-query │  │ /transcribe │  │   /health    │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────────────┘  │   │
│  └─────────┼────────────────┼───────────────────────────┘   │
│            │                │                                │
│            ▼                ▼                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              USER-TYPE ROUTING                       │    │
│  │  ┌────────────────┐  ┌───────────────┐  ┌─────────┐ │    │
│  │  │ Student        │  │ Elderly       │  │ Tourist │ │    │
│  │  │ Optimizer      │  │ Router        │  │ Convo   │ │    │
│  │  │ (Cheap/Fast)   │  │ (Comfort)     │  │ (AI)    │ │    │
│  │  └────────────────┘  └───────────────┘  └─────────┘ │    │
│  └──────────────────────────────────────────────────────┘   │
│            │                │                │               │
│            ▼                ▼                ▼               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              SHARED SERVICES                         │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │    │
│  │  │Intent Parser │  │Hybrid Router │  │ Mapbox    │  │    │
│  │  └──────────────┘  └──────────────┘  └───────────┘  │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │    │
│  │  │Transit Data  │  │   Gemini     │  │Ride Pricing│ │    │
│  │  │   Service    │  │     AI       │  │           │  │    │
│  │  └──────────────┘  └──────────────┘  └───────────┘  │    │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     EXTERNAL APIs                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Mapbox   │  │  Gemini  │  │   Ola    │  │  Uber    │     │
│  │Directions│  │    AI    │  │Deep Links│  │Deep Links│     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## User-Type Specific Processing

### Student Flow

```
Query: "Hebbal to Majestic"
         │
         ▼
┌─────────────────────────────────┐
│     student_optimizer.py        │
│  1. Get hybrid router results   │
│  2. Build all route options     │
│  3. Sort by cost → cheapest     │
│  4. Sort by time → fastest      │
│  5. Return all_options array    │
└─────────────────────────────────┘
         │
         ▼
Response: {
  cheapest: Bus ₹25,
  fastest: Auto ₹132,
  all_options: [Bus, Metro, Auto]
}
```

### Elderly Flow

```
Query: "Jayanagar to Majestic"
         │
         ▼
┌─────────────────────────────────┐
│      elderly_router.py          │
│  1. Build all route options     │
│  2. Calculate comfort score     │
│     - AC: +20, Seating: +15     │
│     - Door-to-door: +25         │
│     - Walking <100m: +20        │
│  3. Sort by comfort score DESC  │
│  4. Return ranked options       │
└─────────────────────────────────┘
         │
         ▼
Response: {
  most_comfortable: Cab (115),
  all_options: [Cab, Auto, Metro, Bus]
}
```

### Tourist Flow

```
Query: "I'm in Hampi for 3 days"
         │
         ▼
┌─────────────────────────────────┐
│   tourist_conversation.py       │
│  1. Extract location + days     │
│  2. Create session state        │
│  3. Ask preference questions    │
│  4. Collect user answers        │
│  5. Call Gemini AI for places   │
│  6. Filter within 50km          │
│  7. Return recommendations      │
└─────────────────────────────────┘
         │
         ▼
Response: {
  type: "question",
  message: "What kind of traveler?",
  options: ["Adventurer", "Culture", ...]
}
```

---

## Backend Services Reference

| Service | File | Purpose |
|---------|------|---------|
| Intent Parser | `intent_parser.py` | Extract origin, destination, city from NL |
| Student Optimizer | `student_optimizer.py` | Cheapest/fastest routes + all options |
| Elderly Router | `elderly_router.py` | Comfort-scored route ranking |
| Tourist Conversation | `tourist_conversation.py` | AI conversational recommendation |
| Hybrid Router | `hybrid_router.py` | Multi-modal route planning |
| Transit Data | `transit_data_service.py` | OpenCity.in data loader |
| Mapbox Directions | `mapbox_directions.py` | Walking directions, geocoding |
| Ride Pricing | `ride_pricing.py` | Ola/Uber/Rapido estimates |
| Translation | `translation_service.py` | Multi-language support |

---

## Dependencies

### Backend (Python)

```
fastapi>=0.100.0
uvicorn>=0.22.0
pydantic>=2.0.0
requests>=2.31.0
python-dotenv>=1.0.0
aiofiles>=23.0.0
python-multipart>=0.0.6
```

### Frontend (Web)

- Vanilla JavaScript (ES6+)
- Web Speech API
- Fetch API
- CSS3 with custom properties

---

## Transit Data Specifications

### Bengaluru BMTC (`bmtc_stops.csv`)

| Column | Type | Description |
|--------|------|-------------|
| Stop Name | string | Official BMTC stop name |
| Latitude | float | GPS latitude |
| Longitude | float | GPS longitude |
| Num trips in stop | int | Daily frequency |
| Routes with num trips | dict | `{'V-500A': 10, '210H': 5}` |

**Total Records:** 2,957 stops

### Static Transit Lines (`transit_lines.json`)

Major routes for fallback when OpenCity data lacks connectivity.

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TOKEN` | Yes | Mapbox API token |
| `GEMINI_API_KEY` | No | Gemini AI for tourist recommendations |
| `OPENAI_API_KEY` | No | OpenAI for AI planning |
| `GOOGLE_MAPS_API_KEY` | No | Traffic data |
| `HUGGINGFACE_API_KEY` | No | Whisper transcription |

### Ports

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 5500 | Static file server |
| Backend | 8000 | FastAPI server |

---

## API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/voice-query` | Process travel query (all user types) |
| GET | `/health` | Server health check |
| POST | `/transcribe` | Audio to text (Whisper) |
| POST | `/translate` | Text translation |

---

## Deployment Notes

### Development

```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
python -m http.server 5500
```

### Production Considerations

1. Use Gunicorn with Uvicorn workers
2. Enable HTTPS
3. Add rate limiting
4. Cache transit data
5. Use Redis for session storage (tourist conversations)
6. Set up Gemini API key for full tourist features
