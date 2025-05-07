import requests

def test_api():
    # Base URL for the API
    base_url = "https://f9ma89kmrg.execute-api.ap-south-1.amazonaws.com/default/mock-interview-api"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Test GET request to /topics
    try:
        print("\nTesting GET /topics request...")
        response = requests.get(f"{base_url}/topics", headers=headers)
        print(f"GET Status Code: {response.status_code}")
        print(f"GET Response Headers: {dict(response.headers)}")
        print(f"GET Response Body: {response.text}")
    except Exception as e:
        print(f"GET Error: {str(e)}")
    
    # Test GET request to /feedback
    try:
        print("\nTesting GET /feedback request...")
        session_id = "Vasudev Chandra_SQL Modelling_1746606670.0591698"
        response = requests.get(f"{base_url}/feedback/{session_id}", headers=headers)
        print(f"GET Feedback Status Code: {response.status_code}")
        print(f"GET Feedback Response Headers: {dict(response.headers)}")
        print(f"GET Feedback Response Body: {response.text}")
    except Exception as e:
        print(f"GET Feedback Error: {str(e)}")
    
    # Test POST request to /init
    try:
        print("\nTesting POST /init request...")
        data = {
            "topic": "SQL Modelling",
            "user_name": "Vasudev Chandra"
        }
        response = requests.post(f"{base_url}/init", headers=headers, json=data)
        print(f"POST Status Code: {response.status_code}")
        print(f"POST Response Headers: {dict(response.headers)}")
        print(f"POST Response Body: {response.text}")
    except Exception as e:
        print(f"POST Error: {str(e)}")

if __name__ == "__main__":
    test_api() 