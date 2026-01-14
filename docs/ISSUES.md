# Current Issues & Debugging Log

## Overview

This document tracks the hybrid transit integration progress, what has been tried, and current issues.

---

## ✅ Completed Successfully

### 1. User-Specific Travel Systems (NEW)

**Problem:** All user types were getting the same basic routing output.

**Solution:** Implemented distinct systems for each user type:

| User Type | Service | Key Feature |
|-----------|---------|-------------|
| Student | `student_optimizer.py` | Returns `all_options` array with cost/time ranking |
| Elderly | `elderly_router.py` | Comfort scoring (AC, seating, walking distance) |
| Tourist | `tourist_conversation.py` | AI conversational flow with Gemini |

**Status:** ✅ All three working

---

### 2. Elderly Comfort Scoring (NEW)

**Problem:** Elderly users needed options ranked by comfort, not just cost/time.

**Solution:** Implemented `calculate_comfort_score()` function:
```python
def calculate_comfort_score(option):
    score = 0
    if option.get("ac"): score += 20
    if option.get("door_to_door"): score += 25
    if option.get("walking_m", 500) < 100: score += 20
    # ... more factors
    return score
```

**Status:** ✅ Comfort scores correctly calculated (max ~115)

---

### 3. Tourist Conversation Flow (NEW)

**Problem:** Tourists needed AI-powered place recommendations, not route planning.

**Solution:** Created `TouristConversationManager` with:
- Location/duration extraction: "I'm in Hampi for 3 days"
- Preference questions: travel style, group type, interests
- Gemini API integration for AI recommendations
- Fallback static recommendations for Hampi, etc.

**Status:** ✅ Conversation flow working, recommendations generated

---

### 4. Intent Parser Fixes

**Problem:** Query "Majestic from Hebbal" was parsing origin as `current_location` instead of `Hebbal`.

**Solution:** Added new regex pattern for "X from Y" format.

**Status:** ✅ Fixed - Origin correctly parsed

---

### 5. City Auto-Detection

**Problem:** System didn't know if user meant Bengaluru or Mumbai.

**Solution:** Added keyword-based city detection with Mumbai keywords list.

**Status:** ✅ Working - Correctly identifies Mumbai vs Bengaluru

---

### 6. OpenCity.in Data Integration

**Problem:** Needed real BMTC bus stop data.

**Solution:** 
- Downloaded BMTC CSV from OpenCity.in (2,957 stops)
- Created `transit_data_service.py` to load and parse
- Created `kml_parser.py` for Mumbai data

**Status:** ✅ Data loading works

---

### 7. Location Aliases

**Problem:** OpenCity uses verbose names but users say short names like "Hebbal".

**Solution:** Added 20+ Bengaluru aliases with coordinates.

**Status:** ✅ Working

---

### 8. Cheapest/Fastest Logic

**Problem:** Walk was showing as "Fastest" and Auto as "Cheapest" (inverted).

**Solution:** Fixed sorting logic in student_optimizer.py.

**Status:** ✅ Fixed

---

## ⚠️ Known Limitations

### 1. Bus Routes Not Always Appearing

**Problem:** When querying between distant areas (e.g., "Hebbal to Majestic"), bus routes may not appear because:
- OpenCity data doesn't provide full route connectivity
- Each stop only knows what routes pass through IT, not the full route path

**Workaround:** System falls back to static `transit_lines.json` data for major routes.

**Future Fix:** Build complete route graph from OpenCity data.

---

### 2. Gemini API for Tourist Recommendations

**Problem:** Full AI recommendations require Gemini API key.

**Workaround:** System uses curated static recommendations for popular destinations (Hampi) when API key is not available.

**Setup:** Add `GEMINI_API_KEY=xxx` to `.env` file.

---

## Testing Commands

```powershell
# Test Student API
$body = @{text="Hebbal to Majestic"; user_type="student"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/voice-query" -Method POST -ContentType "application/json" -Body $body

# Test Elderly API
$body = @{text="Jayanagar to Majestic"; user_type="elderly"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/voice-query" -Method POST -ContentType "application/json" -Body $body

# Test Tourist API
$body = @{text="I'm in Hampi for 3 days"; user_type="tourist"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/voice-query" -Method POST -ContentType "application/json" -Body $body
```

---

## Recent Fixes Log

| Date | Issue | Fix |
|------|-------|-----|
| Jan 14, 2026 | Tourist location parsing | Fixed regex to capture "I'm in Hampi for 3 days" correctly |
| Jan 14, 2026 | Elderly single route | Added all options with comfort scoring |
| Jan 14, 2026 | Student missing options | Added `all_options` array to response |
| Jan 12, 2026 | Geocoding errors | Added city context to Mapbox queries |
| Jan 11, 2026 | Inverted cheapest/fastest | Fixed sort logic |
