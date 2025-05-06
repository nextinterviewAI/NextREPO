import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY")
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def test_start_interview():
    """Test the start_interview endpoint"""
    print("\nTesting /start_interview endpoint...")
    data = {
        "topic": "Python"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/start_interview",
            headers=HEADERS,
            json=data
        )
        response.raise_for_status()
        result = response.json()
        print("Success! Response:")
        print(json.dumps(result, indent=2))
        return result.get("session_id")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def test_interview_turn(session_id, user_answer):
    """Test the interview_turn endpoint"""
    print(f"\nTesting /interview_turn endpoint with session_id: {session_id}")
    data = {
        "session_id": session_id,
        "user_answer": user_answer
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/interview_turn",
            headers=HEADERS,
            json=data
        )
        response.raise_for_status()
        result = response.json()
        print("Success! Response:")
        print(json.dumps(result, indent=2))
        return result.get("next_question")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def test_end_interview(session_id):
    """Test the end_interview endpoint"""
    print(f"\nTesting /end_interview endpoint with session_id: {session_id}")
    data = {
        "session_id": session_id
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/end_interview",
            headers=HEADERS,
            json=data
        )
        response.raise_for_status()
        result = response.json()
        print("Success! Response:")
        print(json.dumps(result, indent=2))
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

def main():
    print("Starting API tests...")
    
    # Test 1: Start Interview
    session_id = test_start_interview()
    if not session_id:
        print("Failed to start interview. Exiting...")
        return
    
    # Test 2: First Interview Turn
    next_question = test_interview_turn(
        session_id,
        "I have been working with Python for 3 years. I'm familiar with data structures, algorithms, and web development using FastAPI."
    )
    if not next_question:
        print("Failed to get next question. Exiting...")
        return
    
    # Test 3: Second Interview Turn
    next_question = test_interview_turn(
        session_id,
        "I've worked on several projects including a REST API using FastAPI, a data analysis tool using pandas, and a web scraper using BeautifulSoup."
    )
    if not next_question:
        print("Failed to get next question. Exiting...")
        return
    
    # Test 4: End Interview
    test_end_interview(session_id)

if __name__ == "__main__":
    main() 