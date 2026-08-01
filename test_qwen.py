import requests

BASE_URL = "http://localhost:1234/v1"

# Get loaded model
models = requests.get(f"{BASE_URL}/models").json()["data"]
print("Models:", models)

model = models[0]["id"]
print("Using model:", model)

response = requests.post(
    f"{BASE_URL}/chat/completions",
    json={
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "Say hello in one sentence."
            }
        ],
        "temperature": 0.7
    },
    timeout=60
)

print("Status:", response.status_code)
print("Response:")
print(response.text)