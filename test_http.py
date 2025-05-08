import requests
import json
import time

def test_http_server():
    base_url = "http://localhost:8080"
    
    # Test status endpoint
    print("Testing status endpoint...")
    try:
        response = requests.get(f"{base_url}/status")
        print(f"Status response: {response.json()}")
    except Exception as e:
        print(f"Error getting status: {str(e)}")
    
    # Test message endpoint
    print("\nTesting message endpoint...")
    try:
        message_data = {"text": "Hello from test script"}
        response = requests.post(f"{base_url}/message", json=message_data)
        print(f"Message response: {response.json()}")
    except Exception as e:
        print(f"Error sending message: {str(e)}")

if __name__ == "__main__":
    test_http_server()