import requests
import json
import base64
import time

BASE_URL = "http://localhost:8000/mock-interview-api"

def test_voice_interview():
    # Initialize interview
    init_response = requests.post(
        f"{BASE_URL}/init",
        json={
            "topic": "SQL Modelling",
            "user_name": "Test Admin"
        }
    )
    print("\nInitializing interview...")
    print(f"Status: {init_response.status_code}")
    print(f"Response: {init_response.json()}\n")
    
    session_id = init_response.json()["session_id"]
    
    # Simulate voice answers with text responses
    sample_answers = [
        "I would start by identifying the core entities in the system and their relationships. For example, in a library system, we'd have books, members, and loans.",
        "For data integrity, I'd use foreign key constraints to maintain referential integrity between related tables. I'd also implement appropriate indexes for frequently queried columns.",
        "I'd use a many-to-many relationship table to handle the relationship between books and authors, since one book can have multiple authors and one author can write multiple books.",
        "For the loan history, I'd create a separate table with foreign keys to both the book and member tables, along with loan date and return date columns."
    ]
    
    for i, answer in enumerate(sample_answers, 1):
        print(f"\nSubmitting answer {i}...")
        
        # Simulate voice input by encoding text as base64
        voice_data = base64.b64encode(answer.encode()).decode()
        
        voice_response = requests.post(
            f"{BASE_URL}/voice-answer",
            json={
                "session_id": session_id,
                "audio_data": voice_data
            }
        )
        
        print(f"Status: {voice_response.status_code}")
        print(f"Response: {voice_response.json()}\n")
        time.sleep(1)  # Add delay between answers
    
    # Get feedback
    print("\nGetting feedback...")
    feedback_response = requests.get(
        f"{BASE_URL}/feedback/{session_id}"
    )
    
    print(f"Status: {feedback_response.status_code}")
    print("\nFeedback:")
    print(json.dumps(feedback_response.json(), indent=2))

if __name__ == "__main__":
    test_voice_interview() 