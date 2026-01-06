"""
Ride-hailing price estimation service.
Provides estimated prices for various ride-hailing services based on distance and surge.
"""

from typing import Dict, List, Tuple
from datetime import datetime


# Base rates updated as of January 2026 for Bengaluru
BASE_RATES = {
    "namma_yatri_auto": {
        "name": "Namma Yatri Auto",
        "base": 25,
        "per_km": 14,
        "category": "auto",
        "description": "Open-source auto booking"
    },
    "ola_auto": {
        "name": "Ola Auto",
        "base": 30,
        "per_km": 15,
        "category": "auto",
        "description": "Standard auto rickshaw"
    },
    "uber_auto": {
        "name": "Uber Auto",
        "base": 30,
        "per_km": 15,
        "category": "auto",
        "description": "UberAuto service"
    },
    "rapido_bike": {
        "name": "Rapido Bike",
        "base": 20,
        "per_km": 8,
        "category": "bike",
        "description": "Bike taxi - fastest for short trips"
    },
    "rapido_auto": {
        "name": "Rapido Auto",
        "base": 28,
        "per_km": 14,
        "category": "auto",
        "description": "Auto via Rapido"
    },
    "ola_micro": {
        "name": "Ola Micro",
        "base": 50,
        "per_km": 12,
        "category": "cab",
        "description": "Economy cab - shared option"
    },
    "uber_go": {
        "name": "Uber Go",
        "base": 55,
        "per_km": 13,
        "category": "cab",
        "description": "Affordable cab rides"
    },
    "ola_prime": {
        "name": "Ola Prime",
        "base": 80,
        "per_km": 16,
        "category": "cab",
        "description": "Sedan with AC"
    },
    "uber_premier": {
        "name": "Uber Premier",
        "base": 85,
        "per_km": 17,
        "category": "cab",
        "description": "Premium sedan"
    }
}


def generate_deep_link(service: str, origin: str, destination: str) -> str:
    """Generate deep link for ride-hailing service."""
    origin_encoded = origin.replace(" ", "%20")
    destination_encoded = destination.replace(" ", "%20")
    
    if "ola" in service:
        return f"https://book.olacabs.com/?pickup={origin_encoded}&drop={destination_encoded}"
    elif "uber" in service:
        return f"https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[formatted_address]={destination_encoded}"
    elif "rapido" in service:
        return f"https://rapido.bike/ride?pickup={origin_encoded}&drop={destination_encoded}"
    elif "namma_yatri" in service:
        return f"https://nammayatri.in/open/?pickup={origin_encoded}&destination={destination_encoded}"
    else:
        return "#"


def calculate_estimated_price(distance_km: float, base: float, per_km: float, surge_multiplier: float = 1.0) -> Tuple[int, Tuple[int, int]]:
    """
    Calculate estimated price and range.
    Returns (estimated_price, (min_price, max_price))
    """
    base_fare = base + (distance_km * per_km)
    surged_fare = base_fare * surge_multiplier
    
    # Add ±10% variance for realistic range
    min_price = int(surged_fare * 0.9)
    max_price = int(surged_fare * 1.1)
    estimated = int(surged_fare)
    
    return estimated, (min_price, max_price)


def get_estimated_ride_prices(
    origin: str,
    destination: str,
    distance_km: float,
    surge_multiplier: float = 1.0,
    user_type: str = "student",
    budget_limit: int = None
) -> Dict:
    """
    Get estimated prices for all available ride-hailing services.
    
    Args:
        origin: Pickup location
        destination: Drop location
        distance_km: Distance in kilometers
        surge_multiplier: Surge pricing multiplier (default 1.0)
        user_type: User type for filtering (elderly/tourist/student)
        budget_limit: Maximum budget for student mode
    
    Returns:
        Dictionary with ride options and recommendations
    """
    ride_options = []
    
    for service_id, rates in BASE_RATES.items():
        estimated, (min_price, max_price) = calculate_estimated_price(
            distance_km, 
            rates["base"], 
            rates["per_km"], 
            surge_multiplier
        )
        
        option = {
            "service": rates["name"],
            "service_id": service_id,
            "category": rates["category"],
            "estimated_price": estimated,
            "price_range": f"₹{min_price}-{max_price}",
            "description": rates["description"],
            "deep_link": generate_deep_link(service_id, origin, destination),
            "surge_applied": surge_multiplier > 1.0
        }
        
        ride_options.append(option)
    
    # Filter based on user type
    ride_options = filter_by_user_type(ride_options, user_type, distance_km)
    
    # Filter by budget if specified
    if budget_limit:
        ride_options = [opt for opt in ride_options if opt["estimated_price"] <= budget_limit]
    
    # Sort by price
    ride_options = sorted(ride_options, key=lambda x: x["estimated_price"])
    
    # Generate recommendation
    recommendation = generate_recommendation(ride_options, user_type, distance_km)
    
    return {
        "ride_options": ride_options,
        "recommendation": recommendation,
        "surge_active": surge_multiplier > 1.0,
        "note": "Prices are estimated. Tap links to see live prices in apps."
    }


def filter_by_user_type(options: List[Dict], user_type: str, distance_km: float) -> List[Dict]:
    """Filter ride options based on user type preferences."""
    
    if user_type == "elderly":
        # Exclude bikes for elderly users (safety)
        options = [opt for opt in options if opt["category"] != "bike"]
        
        # For elderly, prefer comfortable options for long distances
        if distance_km > 10:
            # Prioritize cabs over autos for comfort
            cabs = [opt for opt in options if opt["category"] == "cab"]
            autos = [opt for opt in options if opt["category"] == "auto"]
            return cabs + autos
    
    elif user_type == "tourist":
        # Tourists may prefer known brands (Ola/Uber) over local services
        priority_services = ["ola_", "uber_"]
        prioritized = [opt for opt in options if any(s in opt["service_id"] for s in priority_services)]
        others = [opt for opt in options if opt not in prioritized]
        return prioritized + others
    
    # Default (student mode) - show all options
    return options


def generate_recommendation(options: List[Dict], user_type: str, distance_km: float) -> str:
    """Generate smart recommendation based on user type and distance."""
    
    if not options:
        return "No ride options available within budget"
    
    cheapest = options[0]
    
    if user_type == "student":
        return f"{cheapest['service']} - Most economical (₹{cheapest['estimated_price']})"
    
    elif user_type == "elderly":
        # For elderly, balance cost and comfort
        if distance_km > 10:
            cabs = [opt for opt in options if opt["category"] == "cab"]
            if cabs:
                return f"{cabs[0]['service']} - Comfortable for longer trips (₹{cabs[0]['estimated_price']})"
        return f"{cheapest['service']} - Safe and affordable (₹{cheapest['estimated_price']})"
    
    else:  # tourist
        # Tourists prefer known brands
        ola_uber = [opt for opt in options if "Ola" in opt["service"] or "Uber" in opt["service"]]
        if ola_uber:
            return f"{ola_uber[0]['service']} - Trusted service (₹{ola_uber[0]['estimated_price']})"
        return f"{cheapest['service']} - Best value (₹{cheapest['estimated_price']})"


def is_night_time() -> bool:
    """Check if current time is night (10 PM - 6 AM)."""
    hour = datetime.now().hour
    return hour >= 22 or hour < 6
