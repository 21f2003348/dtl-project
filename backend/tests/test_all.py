"""
Comprehensive test suite for Voice Travel Assistant.
Tests all endpoints, business logic, and integrations.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import the app
import sys
sys.path.insert(0, str(Path(__file__).parent / ".."))

from main import app
from services.route_graph import RouteGraph
from services.group_optimizer import GroupOptimizer
from services.traffic_provider import TrafficProvider
from services.usual_route import UsualRouteManager
from services.gtfs_loader import GTFSDataLoader
from services.tourist_ai_planner import TouristAIPlanner


client = TestClient(app)


# ==================== FIXTURES ====================

@pytest.fixture
def sample_transit_lines():
    """Sample transit data for testing."""
    return {
        "Purple": {
            "line": "Purple Line",
            "stops": ["Challaghatta", "Yeshwantpur", "Vidhana Soudha", "Majestic", "KR Puram", "Whitefield"],
            "coordinates": {
                "Challaghatta": {"lat": 13.0, "lon": 77.5},
                "Yeshwantpur": {"lat": 13.1, "lon": 77.6},
                "Vidhana Soudha": {"lat": 13.19, "lon": 77.59},
                "Majestic": {"lat": 13.20, "lon": 77.61},
                "KR Puram": {"lat": 13.25, "lon": 77.65},
                "Whitefield": {"lat": 13.35, "lon": 77.75}
            }
        }
    }


# ==================== HEALTH ENDPOINT TESTS ====================

class TestHealthEndpoint:
    """Test /health endpoint."""
    
    def test_health_endpoint(self):
        """Test health check returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ==================== VOICE QUERY ENDPOINT TESTS ====================

class TestVoiceQueryEndpoint:
    """Test /voice-query endpoint."""
    
    def test_solo_student_query(self):
        """Test solo student voice query."""
        payload = {
            "user_type": "student",
            "origin": "Whitefield",
            "destination": "Majestic",
            "group_type": "solo",
            "group_size": 1
        }
        response = client.post("/voice-query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "route_options" in data or "route" in data
    
    def test_group_query_student_group(self):
        """Test group query with multiple students."""
        payload = {
            "user_type": "student",
            "origin": "Whitefield",
            "destination": "Majestic",
            "group_type": "student_group",
            "group_size": 3,
            "student_count": 3
        }
        response = client.post("/voice-query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "group_summary" in data or "route_options" in data
    
    def test_elderly_query(self):
        """Test elderly user query."""
        payload = {
            "user_type": "elderly",
            "origin": "Majestic",
            "destination": "Lalbagh",
            "group_type": "elderly_couple",
            "group_size": 2,
            "elderly_count": 2,
            "accessibility_need": True
        }
        response = client.post("/voice-query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_tourist_query(self):
        """Test tourist user query."""
        payload = {
            "user_type": "tourist",
            "origin": "Bengaluru City Airport",
            "destination": "Vidhana Soudha",
            "group_type": "solo",
            "group_size": 1
        }
        response = client.post("/voice-query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_family_query(self):
        """Test family group query."""
        payload = {
            "user_type": "student",
            "origin": "JP Nagar",
            "destination": "Indiranagar",
            "group_type": "family",
            "group_size": 4,
            "children_count": 2
        }
        response = client.post("/voice-query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


# ==================== USUAL ROUTES ENDPOINT TESTS ====================

class TestUsualRoutesEndpoints:
    """Test /usual-routes/* endpoints."""
    
    @pytest.fixture
    def student_id(self):
        return "STU001"
    
    def test_add_usual_route(self, student_id):
        """Test adding a usual route."""
        payload = {
            "student_id": student_id,
            "route_name": "Daily Commute",
            "origin": "Whitefield",
            "destination": "Majestic",
            "frequency": "daily"
        }
        response = client.post("/usual-routes/add", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "route_id" in data
    
    def test_get_usual_routes(self, student_id):
        """Test retrieving usual routes."""
        # First add a route
        add_payload = {
            "student_id": student_id,
            "route_name": "Test Route",
            "origin": "Whitefield",
            "destination": "Jayanagar",
            "frequency": "weekly"
        }
        client.post("/usual-routes/add", json=add_payload)
        
        # Then retrieve
        response = client.get(f"/usual-routes/{student_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "routes" in data
    
    def test_quick_book(self, student_id):
        """Test quick booking a usual route."""
        # Add route first
        add_payload = {
            "student_id": student_id,
            "route_name": "Quick Test",
            "origin": "Whitefield",
            "destination": "Majestic",
            "frequency": "daily"
        }
        add_response = client.post("/usual-routes/add", json=add_payload)
        route_id = add_response.json().get("route_id")
        
        # Quick book
        book_payload = {
            "student_id": student_id,
            "route_id": route_id
        }
        response = client.post("/usual-routes/quick-book", json=book_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_most_used_route(self, student_id):
        """Test retrieving most used route."""
        response = client.get(f"/usual-routes/{student_id}/most-used")
        assert response.status_code in [200, 404]  # 404 if no routes exist


# ==================== TOURIST ENDPOINTS TESTS ====================

class TestTouristEndpoints:
    """Test /tourist/* endpoints."""
    
    def test_get_itinerary(self):
        """Test AI itinerary generation."""
        payload = {
            "city": "Bengaluru",
            "days": 3,
            "interests": ["temples", "markets", "food"],
            "budget": "moderate",
            "travel_style": "explorer"
        }
        response = client.post("/tourist/itinerary", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "itinerary" in data or "days" in data
    
    def test_quick_tips(self):
        """Test getting quick tips for attraction."""
        payload = {
            "place_name": "Vidhana Soudha",
            "city": "Bengaluru"
        }
        response = client.post("/tourist/quick-tips", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "tips" in data
    
    def test_suggested_routes(self):
        """Test getting tourist-friendly routes."""
        response = client.get("/tourist/suggested-routes/Vidhana%20Soudha/Lalbagh")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


# ==================== TRANSIT ENDPOINTS TESTS ====================

class TestTransitEndpoints:
    """Test /transit/* endpoints."""
    
    def test_get_metro_lines(self):
        """Test getting all metro lines."""
        response = client.get("/transit/metro-lines")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "metro_lines" in data
        assert len(data["metro_lines"]) == 3  # Purple, Green, Yellow
    
    def test_get_metro_line_details(self):
        """Test getting specific metro line details."""
        response = client.get("/transit/metro-line/Purple")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "line" in data
    
    def test_get_bus_routes(self):
        """Test getting BMTC bus routes."""
        response = client.get("/transit/bus-routes")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "routes" in data
    
    def test_compare_metro_vs_bus(self):
        """Test metro vs bus comparison."""
        response = client.get("/transit/metro-vs-bus")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "comparison" in data
    
    def test_transit_stats(self):
        """Test getting transit statistics."""
        response = client.get("/transit/transit-stats/Bengaluru")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


# ==================== STUDENT ONBOARDING TESTS ====================

class TestStudentOnboarding:
    """Test /student/* endpoints."""
    
    def test_student_onboard(self):
        """Test student onboarding."""
        payload = {
            "student_id": "TEST_STU001",
            "name": "John Doe",
            "university": "RVCE",
            "budget": 50,
            "home_location": "Whitefield",
            "college_location": "JP Nagar"
        }
        response = client.post("/student/onboard", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_get_student_profile(self):
        """Test retrieving student profile."""
        student_id = "TEST_STU001"
        
        # Onboard first
        onboard_payload = {
            "student_id": student_id,
            "name": "Jane Doe",
            "university": "RVCE",
            "budget": 60,
            "home_location": "Jayanagar",
            "college_location": "JP Nagar"
        }
        client.post("/student/onboard", json=onboard_payload)
        
        # Get profile
        response = client.get(f"/student/profile/{student_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["profile"]["student_id"] == student_id


# ==================== SERVICE UNIT TESTS ====================

class TestRouteGraphService:
    """Test RouteGraph service logic."""
    
    def test_k_shortest_paths(self, sample_transit_lines):
        """Test finding K shortest paths."""
        route_graph = RouteGraph(sample_transit_lines)
        
        paths = route_graph.find_k_shortest_paths("Whitefield", "Majestic", k=2)
        
        assert len(paths) > 0
        assert all("distance_km" in p for p in paths)
        assert all("estimated_time_min" in p for p in paths)


class TestGroupOptimizerService:
    """Test GroupOptimizer service logic."""
    
    def test_solo_optimization(self, sample_transit_lines):
        """Test solo group optimization."""
        optimizer = GroupOptimizer(sample_transit_lines)
        
        result = optimizer.compute_group_options(
            origin="Whitefield",
            destination="Majestic",
            group_type="solo",
            group_size=1
        )
        
        assert result["status"] == "success"
        assert "route_options" in result
    
    def test_student_group_optimization(self, sample_transit_lines):
        """Test student group optimization."""
        optimizer = GroupOptimizer(sample_transit_lines)
        
        result = optimizer.compute_group_options(
            origin="Whitefield",
            destination="Majestic",
            group_type="student_group",
            group_size=3,
            student_count=3
        )
        
        assert result["status"] == "success"
        assert "group_summary" in result


class TestUsualRouteService:
    """Test UsualRouteManager service logic."""
    
    def test_add_and_retrieve_route(self):
        """Test adding and retrieving usual routes."""
        manager = UsualRouteManager()
        
        # Add route
        route_id = manager.add_route(
            student_id="TEST_STU_UNIT",
            route_name="Unit Test Route",
            origin="Whitefield",
            destination="Majestic",
            frequency="daily"
        )
        
        assert route_id is not None
        
        # Retrieve
        routes = manager.get_usual_routes("TEST_STU_UNIT")
        assert len(routes) > 0
        assert routes[0]["route_name"] == "Unit Test Route"


class TestTrafficProviderService:
    """Test TrafficProvider service logic."""
    
    @patch('requests.get')
    def test_traffic_fallback(self, mock_get):
        """Test fallback when APIs are unavailable."""
        mock_get.return_value.status_code = 500
        
        provider = TrafficProvider()
        result = provider.get_traffic_adjusted_time("Whitefield", "Majestic")
        
        assert "estimated_time_min" in result
        assert "traffic_condition" in result


class TestTouristAIPlannerService:
    """Test TouristAIPlanner service logic."""
    
    def test_fallback_itinerary(self):
        """Test fallback itinerary generation."""
        planner = TouristAIPlanner(api_type="ollama")
        
        itinerary = planner.generate_itinerary(
            city="Bengaluru",
            days=3,
            budget="moderate"
        )
        
        assert "days" in itinerary or "title" in itinerary
    
    def test_follow_up_questions(self):
        """Test generating follow-up questions."""
        planner = TouristAIPlanner()
        itinerary = {}
        
        questions = planner.get_follow_up_questions("Bengaluru", itinerary)
        
        assert len(questions) > 0
        assert all("question" in q for q in questions)


class TestGTFSLoaderService:
    """Test GTFSDataLoader service logic."""
    
    def test_fallback_bmtc_routes(self):
        """Test loading fallback BMTC routes."""
        loader = GTFSDataLoader()
        loader.fetch_from_bmtc_api()
        
        assert len(loader.routes) > 0


# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """End-to-end integration tests."""
    
    def test_student_journey_flow(self):
        """Test complete student journey: onboard → query → book usual route."""
        student_id = "INT_TEST_001"
        
        # 1. Onboard student
        onboard_payload = {
            "student_id": student_id,
            "name": "Integration Test User",
            "university": "RVCE",
            "budget": 100,
            "home_location": "Whitefield",
            "college_location": "JP Nagar"
        }
        onboard_response = client.post("/student/onboard", json=onboard_payload)
        assert onboard_response.status_code == 200
        
        # 2. Query route
        query_payload = {
            "user_type": "student",
            "origin": "Whitefield",
            "destination": "JP Nagar",
            "group_type": "solo",
            "group_size": 1
        }
        query_response = client.post("/voice-query", json=query_payload)
        assert query_response.status_code == 200
        
        # 3. Save as usual route
        route_payload = {
            "student_id": student_id,
            "route_name": "Home to College",
            "origin": "Whitefield",
            "destination": "JP Nagar",
            "frequency": "daily"
        }
        route_response = client.post("/usual-routes/add", json=route_payload)
        assert route_response.status_code == 200
    
    def test_tourist_journey_flow(self):
        """Test complete tourist journey: get itinerary → get tips → find routes."""
        # 1. Get itinerary
        itinerary_response = client.post(
            "/tourist/itinerary",
            json={"city": "Bengaluru", "days": 3, "budget": "moderate"}
        )
        assert itinerary_response.status_code == 200
        
        # 2. Get tips for attraction
        tips_response = client.post(
            "/tourist/quick-tips",
            json={"place_name": "Lalbagh Botanical Garden", "city": "Bengaluru"}
        )
        assert tips_response.status_code == 200
        
        # 3. Get metro lines
        metro_response = client.get("/transit/metro-lines")
        assert metro_response.status_code == 200


# ==================== RUN TESTS ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
