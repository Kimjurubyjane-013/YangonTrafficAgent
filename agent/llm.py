import requests

BASE_URL = "http://localhost:1234/v1"


def get_loaded_model():
    """Return the first loaded model ID from LM Studio."""

    try:
        response = requests.get(
            f"{BASE_URL}/models",
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        models = data.get("data", [])

        if not models:
            return None

        return models[0]["id"]

    except requests.exceptions.RequestException:
        return None

    except ValueError:
        return None


def ask_llm(prompt):

    model = get_loaded_model()

    if model is None:
        return (
            "AI Error: No model is loaded in LM Studio.\n"
            "Open LM Studio, load a model, and start the Local API Server."
        )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an AI traffic assistant for Yangon. "
                    "Give short, practical recommendations."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.5,
        "max_tokens": 200
    }

    try:

        response = requests.post(
            f"{BASE_URL}/chat/completions",
            json=payload,
            timeout=60
        )

        # Show HTTP errors directly
        if response.status_code != 200:
            return (
                f"HTTP {response.status_code}\n"
                f"{response.text}"
            )

        data = response.json()

    except requests.exceptions.RequestException as e:
        return f"Connection Error: {e}"

    except ValueError:
        return "AI Error: Invalid JSON received from LM Studio."

    # Normal OpenAI-compatible response
    if "choices" in data and len(data["choices"]) > 0:

        message = data["choices"][0].get("message", {})

        content = message.get("content")

        if content:
            return content.strip()

    # Error response
    if "error" in data:

        error = data["error"]

        if isinstance(error, dict):
            return "AI Error: " + error.get("message", str(error))

        return "AI Error: " + str(error)

    return "AI Error: Unexpected response:\n" + str(data)