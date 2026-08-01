import requests

BASE_URL = "http://localhost:1234/v1"

try:
    response = requests.get(f"{BASE_URL}/models", timeout=5)
    print("Status Code:", response.status_code)
    print(response.json())

except Exception as e:
    print(e)