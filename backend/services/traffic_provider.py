"""
Dynamic traffic provider for real-time routing adjustments.
Supports Mapbox Traffic Layer, Google Maps, and fallback estimates.
"""

from typing import Dict, Tuple, Optional
import os
import requests
from datetime import datetime


class TrafficProvider:
    """Provides real-time traffic data for dynamic route planning."""
    
    def __init__(self, mapbox_token: Optional[str] = None, google_maps_key: Optional[str] = None):
        """
        Initialize traffic provider with available APIs.
        
        Args:
            mapbox_token: Mapbox API token (for traffic layer)
            google_maps_key: Google Maps API key (for real-time traffic)
        """
        self.mapbox_token = mapbox_token or os.getenv("TOKEN")
        self.google_maps_key = google_maps_key or os.getenv("GOOGLE_MAPS_KEY")
    
    def get_traffic_adjusted_time(
        self,
        origin_coords: Tuple[float, float],
        destination_coords: Tuple[float, float],
        distance_km: float,
        base_time_min: float
    ) -> Dict[str, any]:
        """
        Get traffic-adjusted travel time estimate.
        
        Args:
            origin_coords: (latitude, longitude)
            destination_coords: (latitude, longitude)
            distance_km: Distance in kilometers
            base_time_min: Base time estimate without traffic
        
        Returns:
            {
                "estimated_time_min": int,
                "traffic_condition": "free" | "moderate" | "congested" | "severe",
                "traffic_multiplier": float (1.0 = no traffic, 2.0 = double time),
                "delay_min": int,
                "recommendation": str,
                "data_source": str
            }
        """
        
        # Try Google Maps first (most accurate for traffic)
        if self.google_maps_key:
            result = self._get_google_traffic(origin_coords, destination_coords)
            if result:
                return result
        
        # Fallback to Mapbox traffic layer
        if self.mapbox_token:
            result = self._get_mapbox_traffic(origin_coords, destination_coords, distance_km)
            if result:
                return result
        
        # Fallback to time-of-day estimates
        return self._estimate_by_time_of_day(distance_km, base_time_min)
    
    def _get_google_traffic(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> Optional[Dict]:
        """
        Query Google Maps Directions API for real-time traffic.
        
        Requires: GOOGLE_MAPS_KEY environment variable
        Pricing: ~$5-7 per 1000 requests
        """
        if not self.google_maps_key:
            return None
        
        try:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": f"{origin[0]},{origin[1]}",
                "destination": f"{destination[0]},{destination[1]}",
                "departure_time": "now",
                "key": self.google_maps_key
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data.get("routes"):
                route = data["routes"][0]
                leg = route["legs"][0]
                
                duration_traffic = leg.get("duration_in_traffic", {}).get("value", 0) / 60  # Convert to minutes
                duration_normal = leg.get("duration", {}).get("value", 0) / 60
                
                multiplier = duration_traffic / duration_normal if duration_normal > 0 else 1.0
                
                # Classify traffic
                if multiplier < 1.2:
                    condition = "free"
                elif multiplier < 1.5:
                    condition = "moderate"
                elif multiplier < 2.0:
                    condition = "congested"
                else:
                    condition = "severe"
                
                return {
                    "estimated_time_min": int(duration_traffic),
                    "traffic_condition": condition,
                    "traffic_multiplier": round(multiplier, 2),
                    "delay_min": int(duration_traffic - duration_normal),
                    "recommendation": self._get_traffic_recommendation(condition, int(duration_traffic)),
                    "data_source": "Google Maps Real-Time Traffic"
                }
        except Exception as e:
            print(f"[TRAFFIC] Google Maps error: {e}")
        
        return None
    
    def _get_mapbox_traffic(self, origin: Tuple[float, float], destination: Tuple[float, float], distance_km: float) -> Optional[Dict]:
        """
        Query Mapbox Directions API with traffic layer.
        
        Requires: Mapbox token with traffic layer access
        Pricing: Part of standard Mapbox pricing (~$0.50 per 1000 requests)
        """
        if not self.mapbox_token:
            return None
        
        try:
            # Mapbox uses lon,lat order (opposite of normal)
            coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
            url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coords}"
            
            params = {
                "access_token": self.mapbox_token,
                "annotations": "speed,congestion",
                "overview": "full"
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data.get("routes"):
                route = data["routes"][0]
                duration_sec = route.get("duration", 0)
                duration_min = duration_sec / 60
                
                # Analyze congestion from annotations
                congestion_scores = []
                if "congestion" in route.get("legs", [{}])[0]:
                    congestion_scores = route["legs"][0]["congestion"]
                
                if congestion_scores:
                    avg_congestion = sum(congestion_scores) / len(congestion_scores)
                    if avg_congestion < 0.3:
                        condition = "free"
                    elif avg_congestion < 0.6:
                        condition = "moderate"
                    elif avg_congestion < 0.8:
                        condition = "congested"
                    else:
                        condition = "severe"
                else:
                    # Estimate from time
                    expected_time = distance_km * 0.5  # Assume 2 km/min average
                    multiplier = duration_min / expected_time if expected_time > 0 else 1.0
                    
                    if multiplier < 1.2:
                        condition = "free"
                    elif multiplier < 1.5:
                        condition = "moderate"
                    else:
                        condition = "congested"
                
                return {
                    "estimated_time_min": int(duration_min),
                    "traffic_condition": condition,
                    "traffic_multiplier": round(duration_min / max(distance_km * 2, 1), 2),
                    "delay_min": int(max(duration_min - (distance_km * 2), 0)),
                    "recommendation": self._get_traffic_recommendation(condition, int(duration_min)),
                    "data_source": "Mapbox Traffic Layer"
                }
        except Exception as e:
            print(f"[TRAFFIC] Mapbox error: {e}")
        
        return None
    
    def _estimate_by_time_of_day(self, distance_km: float, base_time_min: float) -> Dict:
        """
        Estimate traffic based on time of day (fallback when APIs unavailable).
        Uses historical Bengaluru traffic patterns.
        """
        hour = datetime.now().hour
        day_of_week = datetime.now().weekday()  # 0=Monday, 6=Sunday
        
        # Bengaluru peak hours: 7-10 AM, 5-8 PM on weekdays
        is_peak = (7 <= hour <= 10 or 17 <= hour <= 20) and day_of_week < 5
        
        if is_peak:
            multiplier = 1.8
            condition = "congested"
        elif 10 < hour < 17 and day_of_week < 5:
            multiplier = 1.3
            condition = "moderate"
        elif 20 < hour or hour < 7:
            multiplier = 0.9
            condition = "free"
        else:  # Weekends
            multiplier = 1.1
            condition = "moderate"
        
        adjusted_time = base_time_min * multiplier
        delay = int(adjusted_time - base_time_min)
        
        return {
            "estimated_time_min": int(adjusted_time),
            "traffic_condition": condition,
            "traffic_multiplier": round(multiplier, 2),
            "delay_min": delay,
            "recommendation": self._get_traffic_recommendation(condition, int(adjusted_time)),
            "data_source": "Time-of-Day Estimate (peak: 7-10 AM, 5-8 PM weekdays)"
        }
    
    def _get_traffic_recommendation(self, condition: str, time_min: int) -> str:
        """Generate user-friendly traffic recommendation."""
        recommendations = {
            "free": f"✓ Light traffic - {time_min} min expected",
            "moderate": f"ℹ Moderate traffic - expect ~{time_min} min, leave 5 min early",
            "congested": f"⚠ Heavy traffic - expect ~{time_min} min, leave 15 min early",
            "severe": f"⚠⚠ Severe congestion - expect {time_min} min+, consider alternative routes or public transport"
        }
        return recommendations.get(condition, f"Estimated {time_min} minutes")
    
    def get_peak_hours_for_city(self, city: str = "Bengaluru") -> Dict:
        """Return peak traffic hours for a city."""
        peak_hours = {
            "Bengaluru": {
                "morning_peak": {"start": 7, "end": 10, "severity": "high"},
                "evening_peak": {"start": 17, "end": 20, "severity": "high"},
                "note": "Avoid: 7-10 AM, 5-8 PM on weekdays"
            },
            "Mumbai": {
                "morning_peak": {"start": 8, "end": 11, "severity": "high"},
                "evening_peak": {"start": 18, "end": 21, "severity": "high"},
                "note": "Avoid: 8-11 AM, 6-9 PM on weekdays"
            },
            "Delhi": {
                "morning_peak": {"start": 7, "end": 10, "severity": "extreme"},
                "evening_peak": {"start": 17, "end": 20, "severity": "extreme"},
                "note": "Avoid: 7-10 AM, 5-8 PM on weekdays"
            }
        }
        return peak_hours.get(city, {})
