import os
from typing import Optional, Tuple
import requests
import logging

logger = logging.getLogger(__name__)
MAPBOX_TOKEN_ENV = "TOKEN"


def _get_token() -> Optional[str]:
    token = os.getenv(MAPBOX_TOKEN_ENV)
    if not token:
        logger.warning(f"Mapbox TOKEN not found in environment, using fallback distances")
    return token


def _geocode(query: str, token: str) -> Optional[Tuple[float, float]]:
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"
    params = {"access_token": token, "limit": 1}
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code != 200:
            logger.warning(f"Geocode failed for '{query}': {resp.status_code}")
            return None
        data = resp.json()
        features = data.get("features") or []
        if not features:
            logger.warning(f"No geocode results for '{query}'")
            return None
        coords = features[0].get("center")
        if not coords or len(coords) < 2:
            return None
        logger.info(f"Geocoded '{query}' -> {coords}")
        return float(coords[0]), float(coords[1])
    except Exception as e:
        logger.error(f"Geocode error for '{query}': {e}")
        return None


def get_distance_time_km_min(origin: str, destination: str) -> Tuple[float, float]:
    """Fetch distance (km) and duration (minutes) via Mapbox Directions Matrix. Falls back to (5km, 10min)."""
    token = _get_token()
    if not token:
        logger.info("Using fallback distance/time (no TOKEN)")
        return 5.0, 10.0

    o = _geocode(origin, token)
    d = _geocode(destination, token)
    if not o or not d:
        logger.warning(f"Geocode failed for origin='{origin}' or dest='{destination}', using fallback")
        return 5.0, 10.0

    coords = f"{o[0]},{o[1]};{d[0]},{d[1]}"
    url = f"https://api.mapbox.com/directions-matrix/v1/mapbox/driving/{coords}"
    params = {"access_token": token, "annotations": "distance,duration"}
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code != 200:
            logger.warning(f"Directions matrix failed: {resp.status_code} - {resp.text}")
            return 5.0, 10.0
        matrix = resp.json()
        distances = matrix.get("distances") or []
        durations = matrix.get("durations") or []
        if not distances or not durations:
            logger.warning("No distance/duration in matrix response")
            return 5.0, 10.0
        meters = distances[0][1]
        seconds = durations[0][1]
        km = round(meters / 1000.0, 2)
        minutes = round(seconds / 60.0, 1)
        logger.info(f"Mapbox: {origin} → {destination} = {km}km, {minutes}min")
        return km, minutes
    except Exception as e:
        logger.error(f"Directions matrix error: {e}")
        return 5.0, 10.0
