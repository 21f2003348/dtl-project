# Current Issues & Debugging Log

## Overview

This document tracks the hybrid transit integration progress, what has been tried, and current issues.

---

## ✅ Completed Successfully

### 1. Intent Parser Fixes

**Problem:** Query "Majestic from Hebbal" was parsing origin as `current_location` instead of `Hebbal`.

**Solution:** Added new regex pattern for "X from Y" format:
```python
# Pattern 2.5: "X from Y" without to/go keywords
dest_from = re.search(r"^([a-z0-9\s]+?)\s+from\s+([a-z0-9\s]+?)$", text_lower)
```

**Status:** ✅ Fixed - Origin correctly parsed as "Hebbal"

---

### 2. City Auto-Detection

**Problem:** System didn't know if user meant Bengaluru or Mumbai.

**Solution:** Added keyword-based city detection:
```python
MUMBAI_KEYWORDS = ["dadar", "andheri", "bandra", "kurla", "thane"...]
if any(kw in query for kw in MUMBAI_KEYWORDS):
    return "mumbai"
return "bengaluru"  # Default
```

**Status:** ✅ Working - Correctly identifies Mumbai vs Bengaluru

---

### 3. OpenCity.in Data Integration

**Problem:** Needed real BMTC bus stop data.

**Solution:** 
- Downloaded BMTC CSV from OpenCity.in (2,957 stops)
- Created `transit_data_service.py` to load and parse
- Created `kml_parser.py` for Mumbai data

**Status:** ✅ Data loading works - 2,957 bus stops, 77 metro stations

---

### 4. Location Aliases

**Problem:** OpenCity uses verbose names like "Esteem Mall Hebbala" but users say "Hebbal".

**Solution:** Added 20+ Bengaluru aliases with coordinates:
```python
BENGALURU_ALIASES = {
    "majestic": {"lat": 12.9764, "lon": 77.5707},
    "hebbal": {"lat": 13.0358, "lon": 77.5970},
    # ...
}
```

**Status:** ✅ Working - "Majestic" finds "Kempegowda Bus Station"

---

### 5. Cheapest/Fastest Logic

**Problem:** Walk was showing as "Fastest" and Auto as "Cheapest" (inverted).

**Solution:** Fixed sorting logic:
```python
sorted_by_cost = sorted(all_options, key=lambda x: x['cost'])  # Cheapest
sorted_by_time = sorted(all_options, key=lambda x: x['time'])  # Fastest
```

**Status:** ✅ Fixed

---

### 6. Walking Option Removal

**Problem:** Walking was showing as an option (no one wants to walk 89 mins).

**Solution:** Filtered out Walk mode:
```python
all_options = [opt for opt in all_options if opt['mode'] != 'Walk']
```

**Status:** ✅ Walk no longer shown

---

## ❌ Current Issue: Bus Routes Not Appearing

### Problem

When querying "Hebbal to Majestic", the system returns **Auto** as both cheapest and fastest instead of showing actual BMTC bus routes.

### Diagnosis

1. **Data is loading correctly:**
   - 2,957 BMTC stops loaded
   - Hebbal stop found: "Esteem Mall Hebbala"
   - Majestic stop found: "Kempegowda Bus Station"

2. **Route intersection fails:**
   - Hebbal area has routes like: `V-500A`, `502-DA`, `GKVK-STP`
   - Majestic area has routes like: `KBS-CKA`, `369-CA`, `KBS-KMS`
   - **No common routes between these two specific stops**

3. **Root cause:**
   - OpenCity data has ~3000 stops but doesn't provide route-to-route connectivity
   - Each stop only knows what routes pass through IT, not the full route path
   - Finding "V-500A goes from Hebbal to Majestic" requires a route graph

### What We Tried

**Attempt 1: Single Stop Matching**
```python
origin_routes = origin_stop.get('routes', [])
dest_routes = dest_stop.get('routes', [])
common = origin_routes & dest_routes  # Empty!
```
**Result:** No common routes found (distant stops don't share routes)

**Attempt 2: Area-Based Search (1km radius)**
```python
origin_area_stops = find_stops_in_radius(origin_lat, origin_lon, 1.0)
for stop in origin_area_stops:
    origin_routes.update(stop['routes'])
# Same for destination
common = origin_routes & dest_routes
```
**Result:** Still no common routes (1km radius not wide enough)

**Attempt 3: Wider Area Search (2km radius)**
```python
# Same logic with 2km radius
```
**Result:** Still no matches (Hebbal and Majestic are ~8km apart)

### Why It Fails

The OpenCity.in BMTC data provides:
```
Stop Name | Routes
----------|--------
"Esteem Mall Hebbala" | ['V-500A', '502-DA', 'GKVK-STP']
"Kempegowda Bus Station" | ['KBS-CKA', '369-CA', '176-G']
```

But does NOT provide:
- Full route path (all stops on route V-500A)
- Route connections between distant stops
- Which routes connect different areas

### Potential Solutions

#### Solution A: Build Route Graph (Recommended)

Build a graph where:
- Nodes = bus stops
- Edges = routes connecting stops

```python
# Pre-compute: For each route, find all stops it serves
route_stops = {
    "V-500A": ["Esteem Mall Hebbala", "Mekhri Circle", ..., "Majestic"],
}
```

**Effort:** High - requires processing entire dataset

#### Solution B: Use Static Route Data

Maintain a curated list of known routes:
```python
KNOWN_ROUTES = {
    ("hebbal", "majestic"): ["V-500A", "500-DA", "276"],
    ("whitefield", "majestic"): ["356D", "KBS-335"],
}
```

**Effort:** Low - but not scalable

#### Solution C: Integrate BMTC API

Use BMTC's official API (if available) for route search.

**Effort:** Medium - depends on API availability

#### Solution D: Fallback to Static transit_lines.json

When OpenCity fails, use the existing static data:
```python
if not bus_routes:
    # Fall back to static transit_lines.json
    bus_routes = find_static_route(origin, destination)
```

**Effort:** Low - already have this data

---

## Recommended Next Steps

1. **Quick Fix:** Implement Solution D (fallback to static data)
2. **Medium Term:** Build Solution B (curated routes for major corridors)
3. **Long Term:** Build Solution A (route graph from data)

---

## Testing Commands

```powershell
# Test API
$body = @{text="Hebbal to Majestic"; user_type="student"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/voice-query" -Method POST -ContentType "application/json" -Body $body

# Check if transit data loaded
# (Logs should show: "[TransitDataService] Loaded: Bengaluru (2957 bus stops...")
```
