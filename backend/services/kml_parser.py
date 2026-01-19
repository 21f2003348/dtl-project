"""
KML Parser for OpenCity.in transit data (Mumbai BEST, Suburban Rail).
Parses KML files and extracts station/stop data.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional
import re


def parse_kml_stops(file_path: str) -> List[Dict]:
    """
    Parse KML file and extract stop/station data.
    
    Args:
        file_path: Path to KML file
        
    Returns:
        List of dicts with {name, lat, lon, description, routes}
    """
    stops = []
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # KML namespace
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        # Try with namespace first
        placemarks = root.findall('.//kml:Placemark', ns)
        
        # If no results, try without namespace (some KML files don't use it)
        if not placemarks:
            placemarks = root.findall('.//{http://www.opengis.net/kml/2.2}Placemark')
        
        # Also try plain XML path
        if not placemarks:
            placemarks = root.findall('.//Placemark')
        
        for placemark in placemarks:
            stop_data = _parse_placemark(placemark, ns)
            if stop_data:
                stops.append(stop_data)
                
    except ET.ParseError as e:
        print(f"[KML Parser] Error parsing {file_path}: {e}")
    except FileNotFoundError:
        print(f"[KML Parser] File not found: {file_path}")
        
    return stops


def _parse_placemark(placemark: ET.Element, ns: dict) -> Optional[Dict]:
    """Parse a single Placemark element."""
    
    # Get name
    name_elem = (
        placemark.find('kml:name', ns) or 
        placemark.find('{http://www.opengis.net/kml/2.2}name') or
        placemark.find('name')
    )
    name = name_elem.text.strip() if name_elem is not None and name_elem.text else None
    
    if not name:
        return None
    
    # Get coordinates
    coords_elem = (
        placemark.find('.//kml:coordinates', ns) or
        placemark.find('.//{http://www.opengis.net/kml/2.2}coordinates') or
        placemark.find('.//coordinates')
    )
    
    lat, lon = None, None
    if coords_elem is not None and coords_elem.text:
        coords_text = coords_elem.text.strip()
        # KML format: lon,lat,alt
        parts = coords_text.split(',')
        if len(parts) >= 2:
            try:
                lon = float(parts[0].strip())
                lat = float(parts[1].strip())
            except ValueError:
                pass
    
    if lat is None or lon is None:
        return None
    
    # Get description (may contain route info)
    desc_elem = (
        placemark.find('kml:description', ns) or
        placemark.find('{http://www.opengis.net/kml/2.2}description') or
        placemark.find('description')
    )
    description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
    
    # Try to extract route numbers from description
    routes = _extract_routes(description)
    
    return {
        'name': name,
        'lat': lat,
        'lon': lon,
        'description': description,
        'routes': routes
    }


def _extract_routes(description: str) -> List[str]:
    """Extract route numbers from description text."""
    routes = []
    
    if not description:
        return routes
    
    # Common patterns for bus route numbers
    # e.g., "Routes: 101, 102, 203" or "Bus: A1, A2"
    patterns = [
        r'(?:routes?|bus(?:es)?)\s*:\s*([^\n]+)',  # Routes: X, Y, Z
        r'\b([A-Z]?\d+[A-Z]?(?:\s*,\s*[A-Z]?\d+[A-Z]?)*)\b',  # A1, 101, 2A
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        for match in matches:
            # Split by comma and clean up
            for route in str(match).split(','):
                route = route.strip()
                if route and len(route) <= 10:  # Reasonable route length
                    routes.append(route)
    
    return list(set(routes))  # Remove duplicates


def load_mumbai_best_stops(data_dir: str) -> List[Dict]:
    """Load Mumbai BEST bus stops from KML."""
    kml_path = Path(data_dir) / "mumbai" / "best_stops.kml"
    return parse_kml_stops(str(kml_path))


def load_mumbai_suburban_stations(data_dir: str) -> List[Dict]:
    """Load Mumbai suburban railway stations from KML."""
    kml_path = Path(data_dir) / "mumbai" / "suburban_stations.kml"
    return parse_kml_stops(str(kml_path))


if __name__ == "__main__":
    # Test the parser
    import json
    
    data_dir = Path(__file__).parent.parent / "data"
    
    print("=== Testing KML Parser ===")
    
    # Test BEST stops
    best_stops = load_mumbai_best_stops(str(data_dir))
    print(f"\nMumbai BEST stops loaded: {len(best_stops)}")
    if best_stops:
        print(f"Sample: {json.dumps(best_stops[0], indent=2)}")
    
    # Test Suburban stations
    suburban = load_mumbai_suburban_stations(str(data_dir))
    print(f"\nMumbai Suburban stations loaded: {len(suburban)}")
    if suburban:
        print(f"Sample: {json.dumps(suburban[0], indent=2)}")
