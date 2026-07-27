# agent/llm.py

import requests
import json


LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"


def ask_llm(user_message):

    prompt = f"""
You are a traffic route assistant.

Extract information from the user's request.

Available vehicles:
Car, Bus, Taxi, Ambulance, Fire Truck,
Police, Motorcycle, Bicycle, Walking

Available locations:
Hledan Junction,
Junction Square,
Inya Lake,
Myanmar Plaza,
Yangon General Hospital,
Yangon Central Station,
Sule Pagoda,
Yangon Airport

Return ONLY JSON.

Example:

{{
 "vehicle": "Ambulance",
 "start": "Hledan Junction",
 "destination": "Yangon Airport"
}}

User request:
{user_message}
"""


    response = requests.post(
        LM_STUDIO_URL,
        json={
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1
        }
    )


    result = response.json()


    answer = result["choices"][0]["message"]["content"]


    return json.loads(answer)