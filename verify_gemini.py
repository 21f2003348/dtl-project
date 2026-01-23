import requests
import json
import sys

def verify_gemini():
    url = "http://127.0.0.1:8000/tourist/itinerary"
    payload = {
        "city": "Mysore",
        "num_people": 1,
        "days": 1,
        "interests": ["palaces", "history"],
        "budget_per_person": 3000
    }
    
    print(f"Testing Gemini API with request to {url}...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                print("\nSUCCESS: Itinerary generated successfully!")
                itinerary = data.get("itinerary", {})
                print(f"Title: {itinerary.get('title')}")
                if itinerary.get("days"):
                    print(f"Generated {len(itinerary['days'])} days of plans.")
                    print(f"Sample Day 1 Morning: {itinerary['days'][0].get('morning')}")
                else:
                    print("Warning: itinerary has no days.")
            else:
                print("\nFAILURE: Backend returned error status.")
                print(f"Message: {data.get('message')}")
                print(f"Suggestion: {data.get('suggestion')}")
                if "configure API keys" in str(data.get("suggestion")):
                    print("\nDiagnosis: Gemini API call failed and fallback was triggered.")
        else:
            print(f"\nFAILURE: HTTP {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\nERROR: Request failed: {e}")

if __name__ == "__main__":
    verify_gemini()
