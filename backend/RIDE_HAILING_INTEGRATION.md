# Ride-Hailing API Integration Guide

## Current Implementation

The system includes deep links to Ola, Uber, Rapido, and Namma Yatri with pre-filled pickup/dropoff locations. Users can tap these links to compare prices within each app.

## Real-Time Price Integration Options

### 1. **Ola Play API** (India-specific)

- **Status**: Requires business partnership
- **Access**: https://www.olacabs.com/corporate
- **Pricing**: Enterprise only, no public free tier
- **Features**: Fare estimation, ride booking, tracking
- **Use Case**: Best for volume users (corporate/college tie-ups)

### 2. **Uber API**

- **Status**: Available but requires app approval
- **Access**: https://developer.uber.com/
- **Pricing**: Free tier available (limited requests/month)
- **Features**:
  - Price Estimates V2: Get fare range without user auth
  - Ride Request: Book rides programmatically
- **Implementation**:

  ```python
  # Example: Get price estimate
  import requests

  def get_uber_estimate(start_lat, start_lon, end_lat, end_lon):
      url = "https://api.uber.com/v1.2/estimates/price"
      headers = {"Authorization": f"Token {UBER_SERVER_TOKEN}"}
      params = {
          "start_latitude": start_lat,
          "start_longitude": start_lon,
          "end_latitude": end_lat,
          "end_longitude": end_lon
      }
      response = requests.get(url, headers=headers, params=params)
      return response.json()
  ```

### 3. **Rapido API**

- **Status**: Not publicly available
- **Access**: Business partnerships only (contact: support@rapido.bike)
- **Note**: Primarily for corporate/bulk integrations

### 4. **Namma Yatri API**

- **Status**: Open-source platform (Beckn protocol)
- **Access**: https://nammayatri.in/open/
- **Pricing**: Free (open-source)
- **Features**: Auto fare estimates, ride booking
- **Implementation**: Uses Beckn Protocol (complex but powerful)

## Recommended Approach for DTL Project

### Short-Term (Current Deep Links) ✅

**Pros:**

- No API costs
- No rate limits
- Users see real-time prices in apps
- Works across all platforms

**Cons:**

- Users must leave your app to compare
- Can't show unified price comparison

### Medium-Term (Hybrid Approach) 🎯 **RECOMMENDED**

Combine estimated pricing with deep links:

```python
# backend/services/ride_pricing.py
def get_estimated_ride_prices(distance_km, surge_multiplier=1.0):
    """
    Returns estimated prices based on historical data + surge.
    More accurate than pure calculation, no API dependency.
    """

    # Base rates (updated quarterly from market research)
    BASE_RATES = {
        "auto": {"base": 30, "per_km": 15},  # Traditional auto
        "ola_micro": {"base": 50, "per_km": 12},
        "uber_go": {"base": 55, "per_km": 13},
        "rapido_bike": {"base": 20, "per_km": 8},
        "namma_yatri_auto": {"base": 25, "per_km": 14}
    }

    estimates = {}
    for service, rates in BASE_RATES.items():
        base_fare = rates["base"] + (distance_km * rates["per_km"])
        surged_fare = base_fare * surge_multiplier
        estimates[service] = {
            "estimated_price": int(surged_fare),
            "deep_link": generate_deep_link(service, origin, destination),
            "note": "Tap to see live price in app"
        }

    return estimates
```

**Response format:**

```json
{
  "ride_options": [
    {
      "service": "Namma Yatri Auto",
      "estimated_price": 185,
      "price_range": "₹170-200",
      "deep_link": "https://nammayatri.in/...",
      "note": "Tap to confirm live price"
    },
    {
      "service": "Rapido Bike",
      "estimated_price": 92,
      "price_range": "₹80-100",
      "deep_link": "rapido://...",
      "note": "Fastest for short trips"
    }
  ],
  "recommendation": "Namma Yatri Auto - Best value"
}
```

### Long-Term (API Integration) 🚀

If you get **college partnership** or **small business tier**:

1. **Uber API** (easiest public access):

   - Sign up at https://developer.uber.com/
   - Get `Server Token` (no OAuth needed for price estimates)
   - Implement `get_uber_estimate()` function
   - Cache responses (5 min TTL) to stay under rate limits

2. **Namma Yatri** (open-source, Bengaluru-focused):
   - Use Beckn Protocol for auto estimates
   - Free but complex implementation
   - Best for demonstrating "local-first" approach

## Implementation Priority

### Phase 1: Enhanced Estimates (1-2 hours) 🎯

✅ **Recommended for demo**

- Add `ride_pricing.py` with service-specific base rates
- Include surge multiplier logic (already have `is_peak_hour()`)
- Show price ranges + deep links
- Update student_optimizer to use estimates

### Phase 2: Uber API Only (2-3 hours)

If you can get API access:

- Integrate Uber Price Estimates V2
- Fallback to estimates if API fails/rate-limited
- Show "Live price" badge for Uber, "Estimated" for others

### Phase 3: Full Multi-Provider (Advanced)

For production-ready system:

- Ola corporate partnership (college tie-up)
- Namma Yatri Beckn integration
- Real-time price aggregation

## Constraints to Consider

### Budget Constraints (Student Mode)

```python
def filter_by_budget(ride_options, max_budget):
    """Student optimizer already has budget preference from profile"""
    affordable = [opt for opt in ride_options if opt["estimated_price"] <= max_budget]
    return sorted(affordable, key=lambda x: x["estimated_price"])
```

### Time Constraints (Elderly Mode)

```python
def prioritize_by_time(ride_options, distance_km):
    """For elderly users, prefer faster direct options"""
    # Rapido bike fastest <5km, auto balanced, cab for >10km
    if distance_km < 5:
        return [opt for opt in ride_options if "bike" in opt["service"].lower()]
    elif distance_km > 10:
        return [opt for opt in ride_options if "cab" in opt["service"].lower()]
    return ride_options  # Auto preferred for medium distances
```

### Safety Constraints (All Modes)

```python
def filter_by_safety(ride_options, user_type):
    """For elderly/night travel, exclude bikes"""
    if user_type == "elderly" or is_night_time():
        return [opt for opt in ride_options if "bike" not in opt["service"].lower()]
    return ride_options
```

### Accessibility Constraints (Elderly)

```python
def filter_by_accessibility(ride_options):
    """Prefer services with wheelchair access"""
    # Ola/Uber have wheelchair-accessible vehicle options
    prioritized = [opt for opt in ride_options if opt["service"] in ["ola_prime", "uber_go"]]
    return prioritized + [opt for opt in ride_options if opt not in prioritized]
```

## Testing Without API Access

Use mock responses for demo:

```python
# backend/services/ride_pricing_mock.py
MOCK_RESPONSES = {
    ("Majestic", "Indiranagar", 5.2): {
        "uber_go": {"price": 98, "eta": "3 min"},
        "ola_micro": {"price": 92, "eta": "5 min"},
        "rapido_bike": {"price": 56, "eta": "2 min"},
        "namma_yatri_auto": {"price": 85, "eta": "4 min"}
    }
}

def get_mock_prices(origin, destination, distance_km):
    # Return closest match from mock data
    # Useful for demo/testing before API access
    pass
```

## Summary

**For your DTL project demo:**

1. ✅ Keep current deep links (already working)
2. 🎯 Add enhanced price estimates using historical rates + surge (30 min work)
3. 📊 Show unified comparison table with "Estimated" badge
4. 💡 Highlight "Tap to see live price" for each service

**For future/production:**

- Apply for Uber API access (free tier)
- Contact college administration for Ola corporate tie-up
- Integrate Namma Yatri (Bengaluru-specific, open-source)

This approach gives you a **"better than Google Maps"** experience without needing paid APIs immediately, while keeping the door open for future enhancements.
