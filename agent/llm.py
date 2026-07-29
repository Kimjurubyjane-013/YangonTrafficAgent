import requests


BASE_URL = "http://localhost:1234/v1"


def get_loaded_model():
    """
    Ask LM Studio which model is currently loaded, so we don't
    have to hardcode a model name that may not match.

    Returns the model id string, or None if no model is loaded
    or the server can't be reached.
    """

    try:
        response = requests.get(
            f"{BASE_URL}/models",
            timeout=5
        )

        result = response.json()

        models = result.get("data", [])

        if not models:
            return None

        return models[0]["id"]

    except requests.exceptions.RequestException:
        return None


def ask_llm(prompt):

    model = get_loaded_model()

    if model is None:
        return (
            "AI Error: Could not reach LM Studio, or no model is "
            "currently loaded. Make sure the Local Server is "
            "running and a model is loaded in LM Studio."
        )

    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            json=data,
            timeout=60
        )

        result = response.json()

    except requests.exceptions.RequestException as e:
        return f"AI Error: Could not reach LM Studio ({e})"

    print(result)   # temporary debugging

    if "choices" in result:
        return result["choices"][0]["message"]["content"]

    elif "error" in result:

        error = result["error"]

        # LM Studio / OpenAI-style servers may return the error
        # as a plain string OR as a dict like {"message": "..."}
        if isinstance(error, dict):
            error_text = error.get("message", str(error))
        else:
            error_text = str(error)

        return "AI Error: " + error_text

    else:
        return "Unexpected AI response"