"""
Test script to verify HTTP server connection
"""

import requests
import time
import sys

def test_http_connection(url, max_attempts=3):
    """Test if HTTP server is available and responding."""
    print(f"Testing connection to {url}...")
    
    for attempt in range(max_attempts):
        try:
            print(f"Attempt {attempt + 1}/{max_attempts}...")
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"Success! Server responded with status code {response.status_code}")
                print(f"Response content: {response.text[:200]}...")
                return True
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
        
        if attempt < max_attempts - 1:
            print("Retrying in 2 seconds...")
            time.sleep(2)
    
    print(f"Failed to connect to {url} after {max_attempts} attempts")
    return False

if __name__ == "__main__":
    # Test IPv4 connection
    ipv4_url = "http://127.0.0.1:5000/status"
    ipv4_success = test_http_connection(ipv4_url)
    
    # Test localhost connection
    localhost_url = "http://localhost:5000/status"
    localhost_success = test_http_connection(localhost_url)
    
    # Print summary
    print("\nConnection Test Summary:")
    print(f"IPv4 (127.0.0.1): {'SUCCESS' if ipv4_success else 'FAILED'}")
    print(f"localhost: {'SUCCESS' if localhost_success else 'FAILED'}")
    
    # Exit with appropriate status code
    if ipv4_success or localhost_success:
        print("At least one connection method succeeded!")
        sys.exit(0)
    else:
        print("All connection methods failed!")
        sys.exit(1)