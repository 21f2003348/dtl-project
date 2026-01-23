# Voice Travel Assistant (Bengaluru)

A comprehensive AI-powered travel assistant designed for students, elderly travelers, and tourists in Bengaluru. The system features group-aware routing, transit integration, and AI-generated itineraries.

## 🚀 Project Overview

This project consists of a **FastAPI Backend** and a **Vanilla JS Frontend**, integrated with multiple external APIs for mapping, traffic, and AI intelligence.

### Key Features
- **Smart Routing**: Custom routes for Students (cheapest/fastest), Elderly (safest/accessible), and Tourists (scenic).
- **Public Transit**: Integration with Namma Metro and BMTC Bus data.
- **AI Itineraries**: Generates personalized travel plans using OpenAI/Gemini.
- **Voice Interface**: Speech-to-text support for queries (English, Hindi, Kannada).
- **Real-time Traffic**: Traffic-aware ETA calculations.

---

## 📂 Project Structure

### Backend (`/backend`)
The backend is built with FastAPI and runs on port `8000`.

#### Key Routes (`backend/routes/`)
- `auth_routes.py`: User authentication (Login/Register).
- `tourist_routes.py`: Generates itineraries and quick tips for attractions.
- `student_routes.py`: Optimized routing for students (budget vs speed).
- `transit_routes.py`: Metro and Bus route information.
- `history_routes.py`: User travel history and saved trips.
- `transcription_routes.py`: Handles audio-to-text conversion.
- `translation_routes.py`: Multi-language support services.
- `text_query.py`: Main entry point for natural language query processing.

#### Core Services (`backend/services/`)
- **Routing & Maps**:
  - `mapbox_directions.py`: Wraps Mapbox API for walking/driving directions.
  - `traffic_provider.py`: Fetches real-time traffic from Google Maps or Mapbox.
  - `distance_provider.py`: Calculates distances and times between points.
  - `route_graph.py`: Graph-based routing logic for custom pathfinding.

- **AI & Intelligence**:
  - `tourist_ai_planner.py`: Orchestrates OpenAI/Gemini for itinerary generation.
  - `whisper_stt.py`: Handles Speech-to-Text using Hugging Face/OpenAI Whisper.
  - `intent_parser.py`: Understands user queries (e.g., "Find cheap bus to Majestic").
  - `translation_service.py`: Translates text between English, Hindi, and Kannada.

- **User Optimization**:
  - `student_optimizer.py`: Logic for student-specific route weighting (cost vs time).
  - `elderly_router.py`: Prioritizes comfort and accessibility for seniors.
  - `ride_pricing.py`: Estimates costs for Uber/Ola/Auto.

### Frontend (`/frontend`)
The frontend is a lightweight, responsive web app using vanilla HTML/CSS/JS, running on port `5500`.

- **HTML Pages**:
  - `index.html`: Landing page and user type selection.
  - `tourist.html`: Interface for itinerary generation and attraction discovery.
  - `student.html`: Route finder for students.
  - `elderly.html`: Simplified interface for elderly users.
  - `history.html`: View past trips and saved itineraries.
  - `itineraries.html`: Dedicated view for detailed travel plans.

- **Scripts**:
  - `app.js`: Core application logic, state management, and authentication.
  - `chat.js`: Handles chat interface, voice recording, and displaying messages.

---

## 🌐 External API Integrations

The system leverages several powerful external APIs. Configuration keys must be set in `.env`.

### 1. Mapbox API (Required)
- **Key**: `TOKEN`
- **Usage**:
  - Base maps and visualization.
  - Geocoding (converting place names to coordinates).
  - Driving and walking directions.
  - Traffic layer (fallback).

### 2. Google Maps API (Optional but Recommended)
- **Key**: `GOOGLE_MAPS_API_KEY`
- **Usage**:
  - **Real-time Traffic**: Provides the most accurate traffic congestion data.
  - **Fallback Routing**: Used if Mapbox data is insufficient.
  - **Place Details**: Richer data for locations (ratings, opening hours).

### 3. Gemini AI (Google)
- **Key**: `GEMINI_API_KEY`
- **Usage**:
  - **Tourist Itineraries**: Generates detailed day-wise plans based on interests.
  - **Complex Queries**: Handles "fuzzy" requests that require reasoning.
  - **Priority**: Secondary AI provider (or Primary if configured).

### 4. OpenAI API
- **Key**: `OPENAI_API_KEY`
- **Usage**:
  - **Itinerary Planning**: High-quality generation of travel plans.
  - **Natural Language Understanding**: Parses complex voice queries.
  - **Priority**: Primary AI provider for planning.

### 5. Hugging Face API
- **Key**: `HUGGINGFACE_API_KEY`
- **Usage**:
  - **Speech-to-Text**: Powers the `whisper-large-v3` model for accurate transcription.
  - **Multi-language**: Supports Indian accents and languages (Hindi, Kannada).

---

## 🛠️ Setup & Installation

1. **Backend Setup**:
   ```bash
   cd backend
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   # source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configuration**:
   Copy `.env.example` to `.env` and populate your API keys.
   ```bash
   cp .env.example .env
   ```

3. **Run Backend**:
   ```bash
   python -m uvicorn main:app --reload --port 8000
   ```

4. **Frontend Setup**:
   Simply serve the `frontend` folder.
   ```bash
   cd ../frontend
   python -m http.server 5500
   ```
   Open `http://localhost:5500` in your browser.

---

## 📝 API Endpoints Summary

- **POST /api/voice-query**: Main entry for voice/text commands.
- **POST /api/tourist/itinerary**: Generate personalized travel plans.
- **GET /api/routes/student**: Get optimized student routes.
- **GET /api/transit/bus**: Get next bus arrival times.

See `docs/` for full API documentation.
