"""Manual connectivity check for an optional local model server."""
import requests

BASE_URL = "http://localhost:1234/v1"

if __name__ == "__main__":
    try:
        response = requests.get(f"{BASE_URL}/models", timeout=5)
        print("Status Code:", response.status_code)
        print(response.json())
    except requests.RequestException as error:
        print(error)
