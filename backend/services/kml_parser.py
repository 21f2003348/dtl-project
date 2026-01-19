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
        print(f"[KML Parser] Found {len(placemarks)} placemarks with namespace in {file_path}")
        
        # If no results, try without namespace (some KML files don't use it)
        if not placemarks:
            placemarks = root.findall('.//{http://www.opengis.net/kml/2.2}Placemark')
            print(f"[KML Parser] Found {len(placemarks)} placemarks with full URI in {file_path}")
        
        # Also try plain XML path
        if not placemarks:
            placemarks = root.findall('.//Placemark')
            print(f"[KML Parser] Found {len(placemarks)} placemarks without namespace in {file_path}")
        
        parsed_count = 0
        for i, placemark in enumerate(placemarks):
            # Debug first placemark only
            debug_first = (i == 0)
            stop_data = _parse_placemark(placemark, ns, debug_first=debug_first)
            if stop_data:
                stops.append(stop_data)
                parsed_count += 1
        
        print(f"[KML Parser] Successfully parsed {parsed_count}/{len(placemarks)} placemarks from {file_path}")
                
    except ET.ParseError as e:
        print(f"[KML Parser] Error parsing {file_path}: {e}")
    except FileNotFoundError:
        print(f"[KML Parser] File not found: {file_path}")
    except Exception as e:
        print(f"[KML Parser] Unexpected error parsing {file_path}: {e}")
        
    return stops


def _parse_placemark(placemark: ET.Element, ns: dict, debug_first=False) -> Optional[Dict]:
    """Parse a single Placemark element."""
    
    if debug_first:
        print(f"[DEBUG] Starting _parse_placemark")
    
    # Get name - ElementTree.find() with namespace dict uses {namespace}tagname format
    # NOT the kml:name prefix format
    name_elem = placemark.find('{http://www.opengis.net/kml/2.2}name')
    
    if debug_first:
        print(f"[DEBUG] name_elem={name_elem}")
        if name_elem is not None:
            print(f"[DEBUG] name_elem.text='{name_elem.text}'")
    
    name = name_elem.text.strip() if name_elem is not None and name_elem.text else None
    
    if debug_first:
        print(f"[DEBUG] name after strip='{name}'")
    
    if not name:
        if debug_first:
            print(f"[DEBUG] No name found")
        return None
    
    if debug_first:
        print(f"[DEBUG] Name: '{name}'")
    
    # Get coordinates using correct namespace format
    coords_elem = placemark.find('.//{http://www.opengis.net/kml/2.2}coordinates')
    
    lat, lon = None, None
    if coords_elem is not None and coords_elem.text:
        coords_text = coords_elem.text.strip()
        if debug_first:
            print(f"[DEBUG] Coords text: '{coords_text}'")
        # KML format: lon,lat,alt (or just lon,lat)
        parts = coords_text.split(',')
        if len(parts) >= 2:
            try:
                lon = float(parts[0].strip())
                lat = float(parts[1].strip())
                if debug_first:
                    print(f"[DEBUG] Parsed lat={lat}, lon={lon}")
            except ValueError as e:
                if debug_first:
                    print(f"[DEBUG] ValueError parsing coords: {e}")
    
    if lat is None or lon is None:
        if debug_first:
            print(f"[DEBUG] Coords are None: lat={lat}, lon={lon}")
        return None
    
    # Get description
    desc_elem = placemark.find('{http://www.opengis.net/kml/2.2}description')
    description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
    
    # Try to extract route numbers from description
    routes = _extract_routes(description)
    
    result = {
        'name': name,
        'lat': lat,
        'lon': lon,
        'description': description,
        'routes': routes,
        'mode': 'bus'  # Default to bus mode
    }
    
    if debug_first:
        print(f"[DEBUG] Returning result with name='{name}'")
    
    return result


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
