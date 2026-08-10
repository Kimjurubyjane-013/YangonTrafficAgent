import requests


BASE_URL = "http://localhost:1234/v1"



def get_loaded_model():

    try:

        response = requests.get(
            f"{BASE_URL}/models",
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        models = data.get(
            "data",
            []
        )


        if not models:

            return None


        return models[0]["id"]


    except Exception:

        return None





def ask_llm(prompt):


    model = get_loaded_model()


    if model is None:

        return (
            "AI Error: No model loaded."
        )



    payload = {

        "model": model,


        "messages": [

            {
                "role": "system",

                "content":
                """
You are Yangon Smart Traffic Assistant.

Only explain the provided route data.
Do not invent traffic, weather, delay,
or transportation information.
Keep answers short.
"""
            },


            {
                "role": "user",

                "content": prompt
            }

        ],


        "temperature": 0.2,


        "max_tokens": 100

    }



    try:

        response = requests.post(

            f"{BASE_URL}/chat/completions",

            json=payload,

            timeout=60

        )


        data = response.json()



    except Exception as e:

        return f"AI Error: {e}"




    if "choices" in data:


        return (
            data["choices"][0]
            ["message"]
            ["content"]
            .strip()
        )



    if "error" in data:

        return (
            "AI Error: "
            + str(data["error"])
        )



    return "AI Error: Unknown response"