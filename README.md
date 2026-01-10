# Voice Travel Assistant (Bengaluru)

FastAPI backend that suggests routes, group-aware options, and tourist itineraries. Frontend lives in `frontend/`. Detailed docs are in `docs/`.

## What’s done

- Group-aware routing (solo, student group, family, elderly) with K-shortest paths and traffic fallback
- Usual routes quick-booking
- Tourist AI itineraries (LLM with template fallback)
- Transit data: metro (Purple/Green/Yellow) + BMTC routes + GTFS loader
- Pricing: ride-hailing estimates + student-friendly costs
- Tests: pytest suite covering endpoints and services

## Not done yet / open items

- Real voice/STT: `services/whisper_stt.py` is a stub (no Whisper/audio pipeline yet)
- Docker/production hardening
- Mobile app / WebSocket live updates
- Authentication & rate limiting

## Quick start

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # or: source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Frontend (optional):

```bash
cd ../frontend
python -m http.server 5500
```

## Env vars (.env)

```
TOKEN=your_mapbox_token
OPENAI_API_KEY=your_openai_key   # optional for richer itineraries
OLLAMA_URL=http://localhost:11434 # optional local LLM
GOOGLE_MAPS_API_KEY=...           # optional for traffic
```

## Key endpoints

- POST /voice-query — main router (audio stub + intent + routing)
- POST /student/onboard, GET /student/profile/{id}
- POST /usual-routes/add, POST /usual-routes/quick-book, GET /usual-routes/{student_id}
- POST /tourist/itinerary, POST /tourist/quick-tips, GET /tourist/suggested-routes/{o}/{d}
- GET /transit/metro-lines, GET /transit/bus-routes, POST /transit/next-buses
- GET /health

## Run tests

```bash
cd backend
pytest -v
```

## More details

See `docs/` for architecture, API reference, status, and feature notes.
