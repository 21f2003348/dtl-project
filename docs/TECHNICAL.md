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
│              │   Web Speech API    │                         │
│              │  (Voice Recognition)│                         │
│              └──────────┬──────────┘                         │
└─────────────────────────┼────────────────────────────────────┘
                          │ HTTP POST
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    FastAPI App                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │   │
│  │  │/voice-query │  │  /tourist   │  │   /health    │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────────────┘  │   │
│  └─────────┼────────────────┼───────────────────────────┘   │
│            │                │                                │
│            ▼                ▼                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    SERVICES                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │    │
│  │  │Intent Parser │  │Hybrid Router │  │ AI Planner│  │    │
│  │  └──────────────┘  └──────────────┘  └───────────┘  │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │    │
│  │  │Transit Data  │  │   Mapbox     │  │Ride Pricing│ │    │
│  │  │   Service    │  │  Directions  │  │           │  │    │
│  │  └──────────────┘  └──────────────┘  └───────────┘  │    │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
└──────────────────────────┼───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     EXTERNAL APIs                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Mapbox   │  │  Gemini  │  │   Ola    │  │  Uber    │     │
│  │Directions│  │    AI    │  │Deep Links│  │Deep Links│     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                            │
│  ┌────────────────────┐  ┌────────────────────┐             │
│  │   OpenCity.in      │  │   Static Data      │             │
│  │  - BMTC CSV        │  │  - Metro Stations  │             │
│  │  - Mumbai KML      │  │  - Fare Configs    │             │
│  └────────────────────┘  └────────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Query Processing

```
User Input
    │
    ▼
Intent Parser ──────────────────────────┐
    │                                   │
    ▼                                   │
Parse origin, destination, city         │
    │                                   │
    ▼                                   │
┌───────────────────────────────────────┴─────┐
│            Route by User Type               │
├─────────────────┬─────────────┬─────────────┤
│    Student      │   Elderly   │   Tourist   │
│ student_optimizer│ elderly_router│ ai_planner │
└─────────────────┴─────────────┴─────────────┘
         │                │              │
         ▼                ▼              ▼
┌─────────────────────────────────────────────┐
│             Hybrid Router                   │
│  1. Get coordinates (aliases/geocoding)     │
│  2. Find nearest transit stops              │
│  3. Find connecting routes                  │
│  4. Calculate walking segments              │
│  5. Build multi-modal route                 │
└─────────────────────────────────────────────┘
         │
         ▼
    Response JSON
```

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

### Bengaluru Metro (`metro_stations.json`)

```json
{
  "lines": {
    "Purple": { "stations": [...], "color": "#800080" },
    "Green": { "stations": [...], "color": "#008000" },
    "Yellow": { "stations": [...], "color": "#FFFF00" }
  },
  "fares": {
    "base_fare": 10,
    "per_station": 2,
    "max_fare": 60
  }
}
```

**Total Stations:** 77

---

## Location Alias System

Maps user-friendly names to coordinates:

```python
BENGALURU_ALIASES = {
    "majestic": {"lat": 12.9764, "lon": 77.5707},
    "hebbal": {"lat": 13.0358, "lon": 77.5970},
    "indiranagar": {"lat": 12.9719, "lon": 77.6412},
    "koramangala": {"lat": 12.9352, "lon": 77.6245},
    "whitefield": {"lat": 12.9698, "lon": 77.7500},
    # ... 20+ more locations
}
```

---

## API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/voice-query` | Process travel query |
| GET | `/health` | Server health check |
| POST | `/tourist/plan` | AI itinerary planning |
| POST | `/transcribe` | Audio to text |
| GET | `/geocode/{place}` | Place to coordinates |

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TOKEN` | Yes | Mapbox API token |
| `OPENAI_API_KEY` | No | OpenAI for AI planning |
| `GOOGLE_MAPS_API_KEY` | No | Traffic data |
| `HUGGINGFACE_API_KEY` | No | Whisper transcription |

### Ports

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 5500 | Static file server |
| Backend | 8000 | FastAPI server |

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
5. Use Redis for session storage
